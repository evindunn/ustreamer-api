import contextlib

from fastapi import FastAPI

from .models.db import get_engine
from .routes import base_router
from .settings import get_settings


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application resources during startup."""
    app.state.engine = get_engine(get_settings().db_file)
    yield
    app.state.engine.dispose()


def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    To run with uvicorn, use the following command:
        uvicorn --factory 'ustreamer_api:create_app'
    """
    app = FastAPI(title="ustreamer-api", lifespan=lifespan)
    app.include_router(base_router)
    return app


__all__ = ["create_app"]
