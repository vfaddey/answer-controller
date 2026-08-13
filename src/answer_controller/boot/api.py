import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI

from answer_controller.infrastructure.config import Settings
from answer_controller.infrastructure.di import create_fastapi_container
from answer_controller.presentation.api import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    container = app.state.dishka_container
    await container.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    logging.basicConfig(
        level=resolved_settings.log_level,
        format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":%(message)r}',
    )
    container = create_fastapi_container(resolved_settings)
    application = FastAPI(title="Answer Controller", lifespan=lifespan)
    application.include_router(router)
    frontend = Path(__file__).parents[1] / "presentation" / "static"
    static_router = APIRouter()
    static_router.frontend("/", directory=frontend, fallback="index.html")
    application.include_router(static_router)
    setup_dishka(container, application)
    return application
