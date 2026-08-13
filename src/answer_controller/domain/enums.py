from enum import StrEnum


class EventType(StrEnum):
    CUSTOMER_MESSAGE = "customer_message"
    EMPLOYEE_RESPONSE = "employee_response"


class SlaStatus(StrEnum):
    NORMAL = "normal"
    WARNING = "warning"
    OVERDUE = "overdue"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
