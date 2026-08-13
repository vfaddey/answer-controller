from dishka import Provider, Scope, provide

from answer_controller.application.interactors import (
    CheckSlaInteractor,
    DispatchNotificationsInteractor,
    GetMetricsInteractor,
    HealthInteractor,
    ListTicketsInteractor,
    ProcessEventInteractor,
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


class InteractorProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def process_event(
        self,
        events: EventRepository,
        tickets: TicketRepository,
        tm: TransactionManager,
    ) -> ProcessEventInteractor:
        return ProcessEventInteractor(events, tickets, tm)

    @provide(scope=Scope.REQUEST)
    def list_tickets(self, tickets: TicketRepository) -> ListTicketsInteractor:
        return ListTicketsInteractor(tickets)

    @provide(scope=Scope.REQUEST)
    def get_metrics(self, tickets: TicketRepository) -> GetMetricsInteractor:
        return GetMetricsInteractor(tickets)

    @provide(scope=Scope.REQUEST)
    def check_sla(
        self,
        tickets: TicketRepository,
        outbox: OutboxRepository,
        tm: TransactionManager,
        settings: Settings,
    ) -> CheckSlaInteractor:
        return CheckSlaInteractor(
            tickets,
            outbox,
            tm,
            settings.warning_seconds,
            settings.overdue_seconds,
            settings.sla_batch_size,
        )

    @provide(scope=Scope.REQUEST)
    def dispatch_notifications(
        self,
        outbox: OutboxRepository,
        gateway: NotificationGateway,
        tm: TransactionManager,
        settings: Settings,
    ) -> DispatchNotificationsInteractor:
        return DispatchNotificationsInteractor(outbox, gateway, tm, settings.outbox_batch_size)

    @provide(scope=Scope.REQUEST)
    def health(self, health: HealthRepository) -> HealthInteractor:
        return HealthInteractor(health)
