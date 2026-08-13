from datetime import UTC, datetime

from answer_controller.application.dto import MetricsQuery, MetricsView, TicketView
from answer_controller.application.ports import TicketRepository


class ListTicketsInteractor:
    def __init__(self, tickets: TicketRepository) -> None:
        self._tickets = tickets

    async def execute(self, direction: str | None) -> list[TicketView]:
        return await self._tickets.list_open(direction, datetime.now(UTC))


class GetMetricsInteractor:
    def __init__(self, tickets: TicketRepository) -> None:
        self._tickets = tickets

    async def execute(self, query: MetricsQuery) -> MetricsView:
        return await self._tickets.metrics(query, datetime.now(UTC))
