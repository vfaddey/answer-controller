import asyncio
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from httpx import AsyncClient

from answer_controller.application.interactors import DispatchNotificationsInteractor
from answer_controller.application.ports import NotificationGateway
from answer_controller.domain.entities import OutboxNotification
from answer_controller.domain.enums import OutboxStatus, SlaStatus
from tests.integration.fakes import (
    InMemoryEventRepository,
    InMemoryOutboxRepository,
    InMemoryTicketRepository,
    NoopTransactionManager,
)


class DelayedNotificationGateway(NotificationGateway):
    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def send(self, notification: OutboxNotification) -> None:
        self.started.set()
        await asyncio.sleep(1)


async def test_slow_notification_does_not_block_http_requests(
    api: tuple[AsyncClient, InMemoryEventRepository, InMemoryTicketRepository],
) -> None:
    client, _, _ = api
    outbox = InMemoryOutboxRepository()
    notification = OutboxNotification(
        id=uuid4(),
        ticket_id=uuid4(),
        threshold=SlaStatus.WARNING,
        direction="support",
        status=OutboxStatus.PENDING,
        created_at=datetime.now(UTC),
    )
    outbox.notifications[(notification.ticket_id, notification.threshold)] = notification
    gateway = DelayedNotificationGateway()
    dispatch = asyncio.create_task(
        DispatchNotificationsInteractor(
            outbox,
            gateway,
            NoopTransactionManager(),
            batch_size=10,
        ).execute(),
    )
    await gateway.started.wait()

    started_at = perf_counter()
    health, tickets = await asyncio.gather(client.get("/health"), client.get("/api/tickets"))
    elapsed = perf_counter() - started_at

    assert health.status_code == 200
    assert tickets.status_code == 200
    assert elapsed < 0.5
    assert await dispatch == 1
