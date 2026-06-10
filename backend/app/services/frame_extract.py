from pathlib import Path
import subprocess

from imageio_ffmpeg import get_ffmpeg_exe

from app.core.models import FrameRecord


def extract_frames(video_path: Path, output_dir: Path, every_n: int) -> list[FrameRecord]:
    if every_n < 1:
        raise ValueError("every_n must be >= 1")
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_generated_frames(output_dir)

    temp_pattern = output_dir / "_extract_%06d.png"
    command = [
        get_ffmpeg_exe(),
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"select=not(mod(n\\,{every_n}))",
        "-vsync",
        "0",
        str(temp_pattern),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        _clear_generated_frames(output_dir)
        raise ValueError(f"FFmpeg could not extract frames: {result.stderr.strip()}")

    temp_files = sorted(output_dir.glob("_extract_*.png"))
    if not temp_files:
        raise ValueError(f"FFmpeg extracted no frames from: {video_path}")

    records: list[FrameRecord] = []
    for output_index, temp_file in enumerate(temp_files):
        source_frame = output_index * every_n
        frame_id = f"frame_{source_frame:06d}"
        raw_path = output_dir / f"{frame_id}.png"
        temp_file.replace(raw_path)
        records.append(
            FrameRecord(
                id=frame_id,
                source_frame=source_frame,
                raw_path=str(raw_path),
                keyed_path=None,
                enabled=True,
            )
        )

    return records


def _clear_generated_frames(output_dir: Path) -> None:
    for pattern in ("frame_*.png", "_extract_*.png"):
        for path in output_dir.glob(pattern):
            path.unlink()
