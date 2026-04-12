import certifi
import click
import json
import os
import ssl
import typing
import urllib.request
import uvicorn

from .worker import worker_main

DEFAULT_BASE_URL = "https://picam.localdomain.net/api"


@click.group()
def cli() -> None:
    pass

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


@cli.group()
@click.pass_context
def client(ctx: click.Context) -> None:
    """Run client-side commands against the ustreamer API."""
    ca_certs = os.environ.get("USTREAMER_CA_CERTS")
    ssl_context: ssl.SSLContext | None = None
    if ca_certs:
        ssl_context = ssl.create_default_context()
        ssl_context.load_default_certs()
        ssl_context.load_verify_locations(cafile=certifi.where())
        for ca_cert in (path.strip() for path in ca_certs.split(",") if path.strip()):
            ssl_context.load_verify_locations(cafile=ca_cert)
    ctx.ensure_object(dict)
    ctx.obj["ssl_context"] = ssl_context


@client.command()
@click.option("--base-url", default=DEFAULT_BASE_URL, show_default=True, help="Base URL for the ustreamer API.")
@click.option("--event-duration", default=60.0, show_default=True, type=float, help="Event duration in seconds.")
@click.option("--target-duration", default=10.0, show_default=True, type=float, help="Target timelapse duration in seconds.")
@click.option("--target-fps", default=24.0, show_default=True, type=float, help="Target frames per second.")
@click.pass_context
def create(
    ctx: click.Context,
    base_url: str,
    event_duration: float,
    target_duration: float,
    target_fps: float,
) -> None:
    """Create a timelapse job via the ustreamer API."""
    payload = json.dumps(
        {
            "event_duration": event_duration,
            "target_duration": target_duration,
            "target_fps": target_fps,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/timelapses",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    ssl_context = typing.cast(dict[str, ssl.SSLContext | None], ctx.obj)["ssl_context"]
    with urllib.request.urlopen(request, context=ssl_context) as response:
        click.echo(response.read().decode("utf-8"))
