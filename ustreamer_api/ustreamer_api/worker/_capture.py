import contextlib
import logging
import shutil
import traceback

import httpx
import signal
import time
import typing

from ..models.db import Timelapse
from ..settings import WorkerSettings
from ..settings import get_common_settings
from ._render import render_video


@contextlib.contextmanager
def _graceful_sigint(handler: typing.Callable[[int, typing.Any], None]) -> typing.Iterator[None]:
    """Temporarily install a SIGINT handler and restore the previous one afterwards."""
    previous_sigint_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous_sigint_handler)


def capture_timelapse(logger: logging.Logger, timelapse: Timelapse, settings: WorkerSettings) -> None:
    """Capture frames for a timelapse and render the resulting video."""
    stop_requested = False
    common_settings = get_common_settings()

    image_dir = timelapse.image_dir(common_settings.data_dir)
    image_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    started_at = time.monotonic()
    last_capture_at = started_at - timelapse.shot_interval
    frame_index = 0

    def _handle_sigint(signum: int, frame: typing.Any) -> None:
        """Request capture shutdown after the current loop iteration."""
        nonlocal stop_requested
        stop_requested = True

    with _graceful_sigint(_handle_sigint):
        try:
            with httpx.Client(timeout=2.0) as client:
                while not stop_requested:
                    elapsed = time.monotonic() - started_at
                    if elapsed >= timelapse.event_duration:
                        break

                    if elapsed - (last_capture_at - started_at) >= timelapse.shot_interval:
                        response = client.get(settings.ustreamer_url, params={"action": "snapshot"})
                        response.raise_for_status()
                        frame_path = image_dir / f"frame-{frame_index:06d}.jpg"
                        frame_path.write_bytes(response.content)
                        frame_index += 1
                        last_capture_at = time.monotonic()
                        continue

                    time.sleep(min(0.1, timelapse.shot_interval))
        except Exception as e:
            stop_requested = True
            timelapse.error = str(e)
            logger.warning(f"Error occurred while capturing timelapse {timelapse.id}\n{traceback.format_exc().strip()}\n")

        timelapse.end()

    try:
        if not stop_requested:
                render_video(common_settings.data_dir, timelapse)
    finally:
        shutil.rmtree(image_dir)
