from fastapi import APIRouter

base_router = APIRouter()


@base_router.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
