from sqlalchemy.ext.asyncio import AsyncSession

from answer_controller.application.ports import TransactionManager


class SqlAlchemyTransactionManager(TransactionManager):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
