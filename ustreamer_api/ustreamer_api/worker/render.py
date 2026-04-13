import pathlib
import shutil
import subprocess


def render_video(image_dir: pathlib.Path, target_fps: float, output_file: pathlib.Path) -> None:
    """Render a timelapse video from captured images."""
    if not any(image_dir.glob("frame-*.jpg")):
        return

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(target_fps),
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
    shutil.rmtree(image_dir)
