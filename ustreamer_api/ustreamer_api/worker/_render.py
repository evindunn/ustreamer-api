import pathlib
import shutil
import subprocess

from ..models.db import Timelapse


def render_video(data_dir: pathlib.Path, timelapse: Timelapse) -> None:
    """Render a timelapse video from captured images."""
    image_dir = timelapse.image_dir(data_dir)
    output_file = timelapse.output_file(data_dir)
    
    if not any(image_dir.glob("frame-*.jpg")):
        return

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(timelapse.target_fps),
            "-i",
            str(image_dir / "frame-%06d.jpg"),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(output_file),
        ],
        check=True,
        capture_output=True,
    )
