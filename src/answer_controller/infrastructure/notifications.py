import json
import logging

from answer_controller.application.ports import NotificationGateway
from answer_controller.domain.entities import OutboxNotification


class LoggingNotificationGateway(NotificationGateway):
    def __init__(self) -> None:
        self._logger = logging.getLogger("answer_controller.notifications")

    async def send(self, notification: OutboxNotification) -> None:
        self._logger.info(
            json.dumps(
                {
                    "event": "notification_sent",
                    "notification_id": str(notification.id),
                    "ticket_id": str(notification.ticket_id),
                    "direction": notification.direction,
                    "threshold": notification.threshold,
                },
            ),
        )
