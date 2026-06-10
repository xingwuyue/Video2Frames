from contextlib import contextmanager
import os
from pathlib import Path

import cv2


def probe_video(video_path: Path) -> dict[str, float | int]:
    if not video_path.exists():
        raise FileNotFoundError(video_path)
    if _is_obviously_invalid_mp4(video_path):
        raise ValueError(f"Unreadable video: {video_path}")

    with _suppress_native_stderr():
        capture = cv2.VideoCapture(str(video_path))
        try:
            if not capture.isOpened():
                raise ValueError(f"Unreadable video: {video_path}")

            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

            if width <= 0 or height <= 0 or fps <= 0 or frame_count <= 0:
                raise ValueError(f"Invalid video metadata: {video_path}")

            return {
                "width": width,
                "height": height,
                "fps": fps,
                "frame_count": frame_count,
            }
        finally:
            capture.release()


@contextmanager
def _suppress_native_stderr():
    stderr_fd = 2
    saved_stderr = os.dup(stderr_fd)
    try:
        with open(os.devnull, "w") as devnull:
            os.dup2(devnull.fileno(), stderr_fd)
            yield
    finally:
        os.dup2(saved_stderr, stderr_fd)
        os.close(saved_stderr)


def _is_obviously_invalid_mp4(video_path: Path) -> bool:
    if video_path.suffix.lower() != ".mp4":
        return False

    with video_path.open("rb") as file:
        header = file.read(32)
    return b"ftyp" not in header
