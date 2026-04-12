import click
import uvicorn

from .worker import worker_main


@click.group()
def cli() -> None:
    """Command-line interface for the ustreamer API."""


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Host interface to bind.")
@click.option("--port", default=8000, show_default=True, type=int, help="Port to listen on.")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development.")
def serve(host: str, port: int, reload: bool) -> None:
    """Run the API server."""
    uvicorn.run(
        "ustreamer_api.api:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


@cli.command()
def worker() -> None:
    """Run the background worker."""
    try:
        worker_main()
    except KeyboardInterrupt:
        pass
