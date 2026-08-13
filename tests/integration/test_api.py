import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient

from answer_controller.application.dto import CustomerMessage, ProcessEventCommand
from answer_controller.application.interactors import ProcessEventInteractor
from answer_controller.domain.entities import IncomingEvent
from answer_controller.domain.enums import EventType
from tests.integration.fakes import (
    InMemoryEventRepository,
    InMemoryTicketRepository,
    NoopTransactionManager,
)


class ExpiringRollbackTransactionManager(NoopTransactionManager):
    def __init__(self, event: IncomingEvent) -> None:
        self._event = event

    async def rollback(self) -> None:
        self._event.event_id = "expired"
        self._event.ticket_id = uuid4()


async def test_concurrent_event_delivery_creates_one_ticket(
    api: tuple[AsyncClient, InMemoryEventRepository, InMemoryTicketRepository],
) -> None:
    client, events, tickets = api
    message_id = uuid4()
    event_id = uuid4()
    payload = {
        "event_id": str(event_id),
        "event_type": "customer_message",
        "occurred_at": datetime.now(UTC).isoformat(),
        "payload": {
            "message_id": str(message_id),
            "client_id": "customer-1",
            "channel": "chat",
            "direction": "sales",
            "text": "Help",
        },
    }

    responses = await asyncio.gather(*(client.post("/api/events", json=payload) for _ in range(20)))

    assert all(response.status_code == 201 for response in responses)
    assert sum(not response.json()["duplicate"] for response in responses) == 1
    assert sum(response.json()["duplicate"] for response in responses) == 19
    assert len(events.events) == 1
    assert len(tickets.tickets) == 1

    tickets_response = await client.get("/api/tickets", params={"direction": "sales"})
    assert tickets_response.status_code == 200
    assert [ticket["text"] for ticket in tickets_response.json()] == ["Help"]

    response_event_id = uuid4()
    response = await client.post(
        "/api/events",
        json={
            "event_id": str(response_event_id),
            "event_type": "employee_response",
            "occurred_at": (datetime.now(UTC) + timedelta(seconds=1)).isoformat(),
            "payload": {
                "reply_to_message_id": str(message_id),
                "employee_id": "employee-1",
                "text": "We are on it",
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["ticket_id"] == str(next(iter(tickets.tickets)))
    assert (await client.get("/api/tickets")).json() == []

    duplicate_with_changed_body = await client.post(
        "/api/events",
        json={
            "event_id": str(response_event_id),
            "event_type": "employee_response",
            "occurred_at": (datetime.now(UTC) + timedelta(seconds=2)).isoformat(),
            "payload": {
                "reply_to_message_id": str(uuid4()),
                "employee_id": "another-employee",
                "text": "Changed duplicate payload",
            },
        },
    )
    assert duplicate_with_changed_body.status_code == 201
    assert duplicate_with_changed_body.json()["duplicate"] is True


async def test_metrics_use_crm_occurred_at_and_include_answered_overdue(
    api: tuple[AsyncClient, InMemoryEventRepository, InMemoryTicketRepository],
) -> None:
    client, _, _ = api
    now = datetime.now(UTC)
    messages = [uuid4() for _ in range(4)]
    customer_times = [
        now - timedelta(hours=4),
        now - timedelta(hours=3),
        now - timedelta(hours=2),
        now - timedelta(hours=1),
    ]

    for index, (message_id, occurred_at) in enumerate(zip(messages, customer_times, strict=True)):
        response = await client.post(
            "/api/events",
            json={
                "event_id": str(uuid4()),
                "event_type": "customer_message",
                "occurred_at": occurred_at.isoformat(),
                "payload": {
                    "message_id": str(message_id),
                    "client_id": f"customer-{index}",
                    "channel": "chat",
                    "direction": "support",
                    "text": f"Question {index}",
                },
            },
        )
        assert response.status_code == 201

    for message_id, customer_time, response_seconds in zip(
        messages,
        customer_times,
        (60, 3600, 7200),
        strict=False,
    ):
        response = await client.post(
            "/api/events",
            json={
                "event_id": str(uuid4()),
                "event_type": "employee_response",
                "occurred_at": (customer_time + timedelta(seconds=response_seconds)).isoformat(),
                "payload": {
                    "reply_to_message_id": str(message_id),
                    "employee_id": "employee-1",
                    "text": "Answer",
                },
            },
        )
        assert response.status_code == 201

    response = await client.get(
        "/api/metrics",
        params={
            "date_from": (now - timedelta(hours=5)).isoformat(),
            "date_to": (now + timedelta(hours=1)).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "created": 4,
        "answered": 3,
        "overdue": 3,
        "median_first_response_seconds": 3600.0,
    }

    empty = await client.get(
        "/api/metrics",
        params={
            "date_from": (now + timedelta(days=1)).isoformat(),
            "date_to": (now + timedelta(days=2)).isoformat(),
        },
    )
    assert empty.status_code == 200
    assert empty.json() == {
        "created": 0,
        "answered": 0,
        "overdue": 0,
        "median_first_response_seconds": None,
    }


async def test_duplicate_result_is_copied_before_transaction_rollback() -> None:
    event_id = str(uuid4())
    ticket_id = uuid4()
    now = datetime.now(UTC)
    existing = IncomingEvent.create(
        event_id,
        EventType.CUSTOMER_MESSAGE,
        now,
        {},
        ticket_id,
    )
    events = InMemoryEventRepository()
    events.events[event_id] = existing
    interactor = ProcessEventInteractor(
        events,
        InMemoryTicketRepository(),
        ExpiringRollbackTransactionManager(existing),
    )

    result = await interactor.execute(
        ProcessEventCommand(
            event_id=event_id,
            event_type=EventType.CUSTOMER_MESSAGE,
            occurred_at=now,
            payload=CustomerMessage(uuid4(), "customer", "chat", "sales", "Help"),
        ),
    )

    assert result.event_id == event_id
    assert result.ticket_id == ticket_id
    assert result.duplicate is True
