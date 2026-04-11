from fastapi import APIRouter

base_router = APIRouter()

@base_router.get("/healthz", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
