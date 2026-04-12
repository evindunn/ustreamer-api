from fastapi import APIRouter, status

from .models.db import DatabaseSession, Timelapse
from .models.api import StartTimelapseRequest

base_router = APIRouter()


@base_router.get("/healthz")
async def healthcheck() -> dict[str, str]:
    """Return a simple health status payload."""
    return {"status": "ok"}

@base_router.post(
    "/timelapses",
    response_model=Timelapse,
    status_code=status.HTTP_201_CREATED,
)
async def start_timelapse(
    payload: StartTimelapseRequest,
    db: DatabaseSession,
) -> Timelapse:
    """Create and persist a new timelapse record."""
    timelapse = Timelapse(**payload.model_dump())

    db.add(timelapse)
    db.commit()
    db.refresh(timelapse)

    return timelapse
