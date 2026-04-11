from fastapi import APIRouter, status

from .models.db import DatabaseSession, Timelapse
from .models.api import StartTimelapseRequest, TimelapseResponse

base_router = APIRouter()


@base_router.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

@base_router.post(
    "/timelapses",
    response_model=TimelapseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_timelapse(
    payload: StartTimelapseRequest,
    db: DatabaseSession,
) -> TimelapseResponse:
    timelapse = Timelapse(**payload.model_dump())

    db.add(timelapse)
    db.commit()
    db.refresh(timelapse)

    return timelapse
