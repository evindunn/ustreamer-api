from fastapi import FastAPI

from .routers import base_router


def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    To run with uvicorn, use the following command:
        uvicorn --factory 'ustreamer_api:create_app'
    """
    app = FastAPI(title="ustreamer-api")
    app.include_router(base_router)

    return app


__all__ = ["create_app"]
