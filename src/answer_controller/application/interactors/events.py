from uuid import uuid4

from answer_controller.application.dto import (
    CustomerMessage,
    EmployeeResponse,
    ProcessEventCommand,
    ProcessEventResult,
)
from answer_controller.application.ports import (
    EventRepository,
    TicketRepository,
    TransactionManager,
)
from answer_controller.domain.entities import IncomingEvent, Ticket
from answer_controller.domain.enums import EventType
from answer_controller.domain.errors import TicketNotFoundError


class ProcessEventInteractor:
    def __init__(
        self,
        events: EventRepository,
        tickets: TicketRepository,
        tm: TransactionManager,
    ) -> None:
        self._events = events
        self._tickets = tickets
        self._tm = tm

    async def execute(self, command: ProcessEventCommand) -> ProcessEventResult:
        try:
            existing = await self._events.get(command.event_id)
            if existing is not None:
                result = ProcessEventResult(
                    event_id=existing.event_id,
                    ticket_id=existing.ticket_id,
                    duplicate=True,
                )
                await self._tm.rollback()
                return result
            ticket = None
            if isinstance(command.payload, EmployeeResponse):
                ticket = await self._tickets.get_for_update_by_message_id(
                    command.payload.reply_to_message_id,
                )
                if ticket is None:
                    raise TicketNotFoundError(command.payload.reply_to_message_id)
                ticket_id = ticket.id
            else:
                ticket_id = uuid4()
            event = IncomingEvent.create(
                command.event_id,
                command.event_type,
                command.occurred_at,
                self._payload_dict(command.payload),
                ticket_id,
            )
            if not await self._events.add_if_absent(event):
                existing = await self._events.get(command.event_id)
                if existing is None:
                    raise RuntimeError
                result = ProcessEventResult(
                    event_id=existing.event_id,
                    ticket_id=existing.ticket_id,
                    duplicate=True,
                )
                await self._tm.rollback()
                return result
            if command.event_type is EventType.CUSTOMER_MESSAGE:
                payload = command.payload
                if not isinstance(payload, CustomerMessage):
                    raise TypeError
                await self._tickets.add(
                    Ticket(
                        id=ticket_id,
                        message_id=payload.message_id,
                        client_id=payload.client_id,
                        channel=payload.channel,
                        direction=payload.direction,
                        text=payload.text,
                        created_at=command.occurred_at,
                    ),
                )
            else:
                if ticket is None:
                    raise RuntimeError
                ticket.close(command.occurred_at)
            await self._tm.commit()
        except Exception:
            await self._tm.rollback()
            raise
        return ProcessEventResult(
            event_id=command.event_id,
            ticket_id=ticket_id,
            duplicate=False,
        )

    @staticmethod
    def _payload_dict(payload: CustomerMessage | EmployeeResponse) -> dict[str, object]:
        if isinstance(payload, CustomerMessage):
            return {
                "message_id": str(payload.message_id),
                "client_id": payload.client_id,
                "channel": payload.channel,
                "direction": payload.direction,
                "text": payload.text,
            }
        return {
            "reply_to_message_id": str(payload.reply_to_message_id),
            "employee_id": payload.employee_id,
            "text": payload.text,
        }
