from sqlalchemy import Enum

from answer_controller.domain.enums import EventType, OutboxStatus, SlaStatus

event_type = Enum(
    EventType,
    values_callable=lambda enum: [item.value for item in enum],
    native_enum=False,
    length=32,
)
sla_status = Enum(
    SlaStatus,
    values_callable=lambda enum: [item.value for item in enum],
    native_enum=False,
    length=16,
)
outbox_status = Enum(
    OutboxStatus,
    values_callable=lambda enum: [item.value for item in enum],
    native_enum=False,
    length=16,
)
