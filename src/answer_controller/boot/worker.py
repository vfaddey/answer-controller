from dishka.integrations.taskiq import FromDishka, inject, setup_dishka
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisStreamBroker

from answer_controller.application.interactors import (
    CheckSlaInteractor,
    DispatchNotificationsInteractor,
)
from answer_controller.infrastructure.config import Settings
from answer_controller.infrastructure.di import create_taskiq_container

settings = Settings()
broker = RedisStreamBroker(settings.redis_url, queue_name="answer-controller")


@broker.task(
    task_name="answer_controller.check_sla",
    schedule=[{"interval": 5, "schedule_id": "check-sla"}],
)
@inject(patch_module=True)
async def check_sla(interactor: FromDishka[CheckSlaInteractor]) -> int:
    return await interactor.execute()


@broker.task(
    task_name="answer_controller.dispatch_notifications",
    schedule=[{"interval": 5, "schedule_id": "dispatch-notifications"}],
)
@inject(patch_module=True)
async def dispatch_notifications(
    interactor: FromDishka[DispatchNotificationsInteractor],
) -> int:
    return await interactor.execute()


scheduler = TaskiqScheduler(broker, [LabelScheduleSource(broker)])
container = create_taskiq_container(settings)
setup_dishka(container, broker)
