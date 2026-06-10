from pathlib import Path

import cv2
import numpy as np
import pytest


@pytest.fixture(scope="session")
def tiny_test_video(tmp_path_factory) -> Path:
    video_path = tmp_path_factory.mktemp("videos") / "moving_square.mp4"
    width = 32
    height = 24
    fps = 6.0
    frame_count = 6

    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError("Could not create test MP4 fixture")

    try:
        for index in range(frame_count):
            frame = np.full((height, width, 3), (0, 255, 0), dtype=np.uint8)
            x = 2 + index * 3
            frame[8:16, x : x + 8] = (0, 0, 255)
            writer.write(frame)
    finally:
        writer.release()

    return video_path
