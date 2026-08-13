from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from answer_controller.application.dto import MetricsQuery, MetricsView, TicketView
from answer_controller.domain.entities import IncomingEvent, OutboxNotification, Ticket


class TransactionManager(ABC):
    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError


class EventRepository(ABC):
    @abstractmethod
    async def add_if_absent(self, event: IncomingEvent) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, event_id: str) -> IncomingEvent | None:
        raise NotImplementedError


class TicketRepository(ABC):
    @abstractmethod
    async def add(self, ticket: Ticket) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_for_update_by_message_id(self, message_id: UUID) -> Ticket | None:
        raise NotImplementedError

    @abstractmethod
    async def list_open(self, direction: str | None, now: datetime) -> list[TicketView]:
        raise NotImplementedError

    @abstractmethod
    async def lock_open_batch(self, limit: int) -> list[Ticket]:
        raise NotImplementedError

    @abstractmethod
    async def metrics(self, query: MetricsQuery, now: datetime) -> MetricsView:
        raise NotImplementedError


class OutboxRepository(ABC):
    @abstractmethod
    async def add_many_if_absent(self, notifications: list[OutboxNotification]) -> int:
        raise NotImplementedError

    @abstractmethod
    async def claim_batch(self, limit: int) -> list[OutboxNotification]:
        raise NotImplementedError


class NotificationGateway(ABC):
    @abstractmethod
    async def send(self, notification: OutboxNotification) -> None:
        raise NotImplementedError


class HealthRepository(ABC):
    @abstractmethod
    async def is_ready(self) -> bool:
        raise NotImplementedError
