from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from answer_controller.application.ports import HealthRepository


class SqlAlchemyHealthRepository(HealthRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def is_ready(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True
