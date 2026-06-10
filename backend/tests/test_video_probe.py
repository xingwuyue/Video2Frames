import pytest

from app.services.video_probe import probe_video


def test_probe_video_returns_basic_metadata(tiny_test_video):
    metadata = probe_video(tiny_test_video)

    assert metadata["width"] == 32
    assert metadata["height"] == 24
    assert metadata["fps"] == pytest.approx(6.0)
    assert metadata["frame_count"] == 6


def test_probe_video_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        probe_video(tmp_path / "missing.mp4")


def test_probe_video_raises_for_invalid_video(tmp_path):
    invalid_video = tmp_path / "invalid.mp4"
    invalid_video.write_text("not a video", encoding="utf-8")

    with pytest.raises(ValueError):
        probe_video(invalid_video)
