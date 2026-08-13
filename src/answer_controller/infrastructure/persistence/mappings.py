from answer_controller.domain.entities import IncomingEvent, OutboxNotification, Ticket
from answer_controller.infrastructure.persistence.tables import (
    incoming_events,
    mapper_registry,
    outbox_notifications,
    tickets,
)

mapped_entities = (
    mapper_registry.map_imperatively(Ticket, tickets),
    mapper_registry.map_imperatively(IncomingEvent, incoming_events),
    mapper_registry.map_imperatively(OutboxNotification, outbox_notifications),
)
