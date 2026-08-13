from answer_controller.application.ports import HealthRepository


class HealthInteractor:
    def __init__(self, health: HealthRepository) -> None:
        self._health = health

    async def execute(self) -> bool:
        return await self._health.is_ready()
