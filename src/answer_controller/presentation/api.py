from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, HTTPException, Query, status

from answer_controller.application.dto import MetricsView, ProcessEventResult, TicketView
from answer_controller.application.interactors import (
    GetMetricsInteractor,
    HealthInteractor,
    ListTicketsInteractor,
    ProcessEventInteractor,
)
from answer_controller.domain.errors import InvalidResponseTimeError, TicketNotFoundError
from answer_controller.presentation.schemas import (
    CustomerMessageEvent,
    EmployeeResponseEvent,
    HealthResponse,
    MetricsParameters,
)

router = APIRouter()


@router.post(
    "/api/events",
    response_model=ProcessEventResult,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def process_event(
    event: CustomerMessageEvent | EmployeeResponseEvent,
    interactor: FromDishka[ProcessEventInteractor],
) -> ProcessEventResult:
    try:
        result = await interactor.execute(event.to_command())
    except TicketNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer message not found") from error
    except InvalidResponseTimeError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Response predates ticket",
        ) from error
    return result


@router.get("/api/tickets", response_model=list[TicketView])
@inject
async def list_tickets(
    interactor: FromDishka[ListTicketsInteractor],
    direction: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
) -> list[TicketView]:
    return await interactor.execute(direction)


@router.get("/api/metrics", response_model=MetricsView)
@inject
async def get_metrics(
    interactor: FromDishka[GetMetricsInteractor],
    parameters: Annotated[MetricsParameters, Query()],
) -> MetricsView:
    return await interactor.execute(parameters.to_query())


@router.get("/health", response_model=HealthResponse)
@inject
async def health(interactor: FromDishka[HealthInteractor]) -> HealthResponse:
    if not await interactor.execute():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database is unavailable")
    return HealthResponse(status="ok")
