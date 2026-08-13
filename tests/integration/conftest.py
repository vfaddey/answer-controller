from collections.abc import AsyncIterator

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
