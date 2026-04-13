import fastapi
import shutil
import sqlalchemy
import uuid
import fastapi.responses

from .models.db import DatabaseSession, Timelapse
from .models.api import StartTimelapseRequest
from .settings import get_common_settings

base_router = fastapi.APIRouter()


@base_router.get("/healthz")
async def healthcheck() -> dict[str, str]:
    """Return a simple health status payload."""
    return {"status": "ok"}


@base_router.get(
    "/timelapses",
    response_model=list[Timelapse],
)
async def list_timelapses(
    db: DatabaseSession,
    limit: int = fastapi.Query(default=100, ge=1),
    offset: int = fastapi.Query(default=0, ge=0),
) -> list[Timelapse]:
    """Return timelapses sorted by start time with pagination."""
    statement = (
        sqlalchemy
        .select(Timelapse)
        .order_by(Timelapse.started_at)
        .offset(offset)
        .limit(limit)
    )
    return list(db.execute(statement).scalars())


@base_router.get(
    "/timelapses/{timelapse_id}",
    response_model=Timelapse,
)
async def get_timelapse(
    timelapse_id: uuid.UUID,
    db: DatabaseSession,
) -> Timelapse:
    """Return a single timelapse by id."""
    timelapse = db.get(Timelapse, timelapse_id)
    if timelapse is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Timelapse not found",
        )
    return timelapse


@base_router.get("/timelapses/{timelapse_id}/video")
async def download_timelapse_video(
    timelapse_id: uuid.UUID,
    db: DatabaseSession,
) -> fastapi.responses.FileResponse:
    """Return the rendered video for a completed timelapse."""
    timelapse = db.get(Timelapse, timelapse_id)
    if timelapse is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Timelapse not found",
        )
    if timelapse.ended_at is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Timelapse is still in progress",
        )

    output_file = timelapse.output_file(get_common_settings().data_dir)
    if not output_file.exists():
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Timelapse video not found",
        )

    return fastapi.responses.FileResponse(
        output_file,
        media_type="video/mp4",
        filename=output_file.name,
    )


@base_router.delete(
    "/timelapses/{timelapse_id}",
    status_code=fastapi.status.HTTP_204_NO_CONTENT,
)
async def delete_timelapse(
    timelapse_id: uuid.UUID,
    db: DatabaseSession,
) -> fastapi.Response:
    """Delete a timelapse and any generated on-disk resources."""
    timelapse = db.get(Timelapse, timelapse_id)
    if timelapse is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Timelapse not found",
        )

    data_dir = get_common_settings().data_dir
    image_dir = timelapse.image_dir(data_dir)
    output_file = timelapse.output_file(data_dir)

    if image_dir.exists():
        shutil.rmtree(image_dir)
    if output_file.exists():
        output_file.unlink()

    db.delete(timelapse)
    db.commit()
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@base_router.post(
    "/timelapses",
    response_model=Timelapse,
    status_code=fastapi.status.HTTP_201_CREATED,
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
