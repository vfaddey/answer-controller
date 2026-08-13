from collections.abc import AsyncIterable

from dishka import Provider, Scope, from_context, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from answer_controller.application.ports import (
    EventRepository,
    HealthRepository,
    NotificationGateway,
    OutboxRepository,
    TicketRepository,
    TransactionManager,
)
from answer_controller.infrastructure.config import Settings
from answer_controller.infrastructure.notifications import LoggingNotificationGateway
from answer_controller.infrastructure.persistence.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyHealthRepository,
    SqlAlchemyOutboxRepository,
    SqlAlchemyTicketRepository,
)
from answer_controller.infrastructure.persistence.transaction_manager import (
    SqlAlchemyTransactionManager,
)


class PersistenceProvider(Provider):
    settings = from_context(provides=Settings, scope=Scope.APP)

    @provide(scope=Scope.APP)
    async def engine(self, settings: Settings) -> AsyncIterable[AsyncEngine]:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        yield engine
        await engine.dispose()

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def session(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> AsyncIterable[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.rollback()

    @provide(scope=Scope.REQUEST)
    def transaction_manager(self, session: AsyncSession) -> TransactionManager:
        return SqlAlchemyTransactionManager(session)

    @provide(scope=Scope.REQUEST)
    def events(self, session: AsyncSession) -> EventRepository:
        return SqlAlchemyEventRepository(session)

    @provide(scope=Scope.REQUEST)
    def tickets(self, session: AsyncSession, settings: Settings) -> TicketRepository:
        return SqlAlchemyTicketRepository(
            session,
            settings.warning_seconds,
            settings.overdue_seconds,
        )

    @provide(scope=Scope.REQUEST)
    def outbox(self, session: AsyncSession) -> OutboxRepository:
        return SqlAlchemyOutboxRepository(session)

    @provide(scope=Scope.APP)
    def notification_gateway(self) -> NotificationGateway:
        return LoggingNotificationGateway()

    @provide(scope=Scope.APP)
    def health(self, engine: AsyncEngine) -> HealthRepository:
        return SqlAlchemyHealthRepository(engine)
