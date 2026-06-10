from pathlib import Path

import pytest

from app.services.frame_extract import extract_frames


def test_extract_frames_writes_every_n_frame_and_records_source_numbers(
    tiny_test_video, tmp_path
):
    records = extract_frames(tiny_test_video, tmp_path / "frames", every_n=2)

    assert [record.source_frame for record in records] == [0, 2, 4]
    assert [record.id for record in records] == [
        "frame_000000",
        "frame_000002",
        "frame_000004",
    ]
    assert [Path(record.raw_path).name for record in records] == [
        "frame_000000.png",
        "frame_000002.png",
        "frame_000004.png",
    ]
    assert [record.keyed_path for record in records] == [None, None, None]
    assert [record.enabled for record in records] == [True, True, True]
    assert len(list((tmp_path / "frames").glob("*.png"))) == 3


def test_extract_frames_removes_stale_frame_files(tiny_test_video, tmp_path):
    output_dir = tmp_path / "frames"
    output_dir.mkdir()
    (output_dir / "frame_999999.png").write_bytes(b"stale")

    extract_frames(tiny_test_video, output_dir, every_n=3)

    assert sorted(path.name for path in output_dir.glob("*.png")) == [
        "frame_000000.png",
        "frame_000003.png",
    ]


@pytest.mark.parametrize("every_n", [0, -1])
def test_extract_frames_rejects_invalid_interval(tiny_test_video, tmp_path, every_n):
    with pytest.raises(ValueError):
        extract_frames(tiny_test_video, tmp_path / "frames", every_n=every_n)
