from datetime import UTC, datetime

from answer_controller.application.ports import (
    NotificationGateway,
    OutboxRepository,
    TransactionManager,
)


class DispatchNotificationsInteractor:
    def __init__(
        self,
        outbox: OutboxRepository,
        gateway: NotificationGateway,
        tm: TransactionManager,
        batch_size: int,
    ) -> None:
        self._outbox = outbox
        self._gateway = gateway
        self._tm = tm
        self._batch_size = batch_size

    async def execute(self) -> int:
        notifications = await self._outbox.claim_batch(self._batch_size)
        await self._tm.commit()
        sent = 0
        for notification in notifications:
            try:
                await self._gateway.send(notification)
            except Exception as error:
                notification.mark_failed(str(error))
            else:
                notification.mark_sent(datetime.now(UTC))
                sent += 1
        await self._tm.commit()
        return sent
