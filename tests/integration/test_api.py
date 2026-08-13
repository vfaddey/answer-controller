import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from answer_controller.application.interactors import (
    GetMetricsInteractor,
    HealthInteractor,
    ListTicketsInteractor,
    ProcessEventInteractor,
)
from answer_controller.domain.entities import Ticket
from answer_controller.presentation.api import router
from tests.integration.fakes import (
    InMemoryEventRepository,
    InMemoryTicketRepository,
    NoopTransactionManager,
    ReadyHealthRepository,
)


class ApplicationProvider(Provider):
    def __init__(
        self,
        events: InMemoryEventRepository,
        tickets: InMemoryTicketRepository,
    ) -> None:
        super().__init__()
        self._events = events
        self._tickets = tickets

    @provide(scope=Scope.REQUEST)
    def process_event(self) -> ProcessEventInteractor:
        return ProcessEventInteractor(self._events, self._tickets, NoopTransactionManager())

    @provide(scope=Scope.REQUEST)
    def list_tickets(self) -> ListTicketsInteractor:
        return ListTicketsInteractor(self._tickets)

    @provide(scope=Scope.REQUEST)
    def get_metrics(self) -> GetMetricsInteractor:
        return GetMetricsInteractor(self._tickets)

    @provide(scope=Scope.REQUEST)
    def health(self) -> HealthInteractor:
        return HealthInteractor(ReadyHealthRepository())


@pytest.fixture
async def api() -> AsyncIterator[
    tuple[AsyncClient, InMemoryEventRepository, InMemoryTicketRepository]
]:
    events = InMemoryEventRepository()
    tickets = InMemoryTicketRepository()
    app = FastAPI()
    app.include_router(router)
    container = make_async_container(ApplicationProvider(events, tickets), FastapiProvider())
    setup_dishka(container, app)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, events, tickets
    await container.close()


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


async def test_metrics_endpoint_returns_fixed_dataset(
    api: tuple[AsyncClient, InMemoryEventRepository, InMemoryTicketRepository],
) -> None:
    client, _, tickets = api
    now = datetime.now(UTC)
    first = Ticket(uuid4(), uuid4(), "c-1", "chat", "sales", "One", now - timedelta(minutes=10))
    second = Ticket(uuid4(), uuid4(), "c-2", "chat", "sales", "Two", now - timedelta(minutes=9))
    overdue = Ticket(
        uuid4(), uuid4(), "c-3", "chat", "support", "Three", now - timedelta(minutes=8)
    )
    first.close(first.created_at + timedelta(seconds=20))
    second.close(second.created_at + timedelta(seconds=40))
    tickets.tickets = {ticket.id: ticket for ticket in (first, second, overdue)}

    response = await client.get(
        "/api/metrics",
        params={
            "date_from": (now - timedelta(hours=1)).isoformat(),
            "date_to": (now + timedelta(minutes=1)).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "created": 3,
        "answered": 2,
        "overdue": 1,
        "median_first_response_seconds": 30.0,
    }
