from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import FastapiProvider
from dishka.integrations.taskiq import TaskiqProvider

from answer_controller.infrastructure.config import Settings
from answer_controller.infrastructure.di.interactors import InteractorProvider
from answer_controller.infrastructure.di.persistence import PersistenceProvider


def create_fastapi_container(settings: Settings) -> AsyncContainer:
    return make_async_container(
        PersistenceProvider(),
        InteractorProvider(),
        FastapiProvider(),
        context={Settings: settings},
    )


def create_taskiq_container(settings: Settings) -> AsyncContainer:
    return make_async_container(
        PersistenceProvider(),
        InteractorProvider(),
        TaskiqProvider(),
        context={Settings: settings},
    )
