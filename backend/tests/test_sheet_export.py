import json
from pathlib import Path

import pytest
from PIL import Image

from app.core.models import AnchorConfig, ExportConfig, FrameRecord, ProjectConfig
from app.services.sheet_export import export_sheet


def test_default_export_uses_352_cell_height_200_and_fixed_pivot_metadata(tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    records = [
        _write_character_frame(frames_dir / f"frame_{index:06d}.png", f"frame_{index:06d}", index)
        for index in range(7)
    ]
    project = ProjectConfig(name="test-project", root=tmp_path, frames=records)

    result = export_sheet(project, tmp_path / "export")

    with Image.open(result["sheet"]) as sheet:
        assert sheet.size == (2112, 704)
        assert sheet.mode == "RGBA"

    metadata = json.loads(result["metadata"].read_text(encoding="utf-8"))
    assert metadata["sheet"] == "sheet.png"
    assert metadata["version"] == "v2_height_fixed_baseline"
    assert metadata["cell_width"] == 352
    assert metadata["cell_height"] == 352
    assert metadata["rows"] == 2
    assert metadata["columns"] == 6
    assert metadata["frame_count"] == 7
    assert metadata["sampling"]["take_every_n_frames"] == 3
    assert metadata["scale_policy"]["mode"] == "fixed_height_shared_scale"
    assert metadata["alignment"] == {
        "horizontal": "bbox_center_fallback",
        "center_x": 176,
        "vertical": "foot_baseline",
        "baseline_y": 320,
    }
    assert metadata["height_region"] == {"top_y": 120, "bottom_y": 320, "height": 200}
    assert metadata["pivot"] == {"x": 176, "y": 320}
    assert metadata["oversize_policy"]["allow_width_variation"] is True
    assert len(metadata["frames"]) == 7
    assert metadata["frames"][6]["x"] == 0
    assert metadata["frames"][6]["y"] == 352


def test_export_rejects_enabled_frames_over_capacity_when_auto_layout_disabled(tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    records = [
        _write_character_frame(frames_dir / f"frame_{index:06d}.png", f"frame_{index:06d}", index)
        for index in range(5)
    ]
    project = _project(
        tmp_path,
        records,
        export=ExportConfig(rows=2, columns=2, auto_layout=False),
    )

    with pytest.raises(ValueError, match="帧数超过当前表格容量。"):
        export_sheet(project, tmp_path / "export")


def test_export_skips_disabled_frames(tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    enabled = _write_character_frame(frames_dir / "frame_000000.png", "frame_000000", 0)
    disabled = _write_character_frame(frames_dir / "frame_000001.png", "frame_000001", 1, enabled=False)
    project = _project(tmp_path, [enabled, disabled])

    result = export_sheet(project, tmp_path / "export")

    metadata = json.loads(result["metadata"].read_text(encoding="utf-8"))
    assert metadata["frame_count"] == 1
    assert [frame["id"] for frame in metadata["frames"]] == ["frame_000000"]


def test_export_uses_shared_height_scale_instead_of_per_frame_scale(tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    records = [
        _write_character_frame(frames_dir / "short.png", "short", 0, bbox=(108, 30, 148, 119)),
        _write_character_frame(frames_dir / "reference.png", "reference", 1, bbox=(108, 20, 148, 119)),
        _write_character_frame(frames_dir / "tall.png", "tall", 2, bbox=(108, 10, 148, 119)),
    ]
    project = _project(tmp_path, records)

    result = export_sheet(project, tmp_path / "export")

    metadata = json.loads(result["metadata"].read_text(encoding="utf-8"))
    scales = {frame["normalization"]["scale"] for frame in metadata["frames"]}
    heights = [frame["normalization"]["normalized_bbox"]["height"] for frame in metadata["frames"]]

    assert metadata["scale_policy"]["reference_height"] == 100
    assert metadata["scale_policy"]["scale"] == pytest.approx(2.0)
    assert len(scales) == 1
    assert heights == [180, 200, 220]


def test_export_aligns_detected_foot_to_baseline_y_320(tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    record = _write_character_frame(
        frames_dir / "frame_000000.png",
        "frame_000000",
        0,
        bbox=(100, 20, 156, 119),
    )
    project = _project(tmp_path, [record])

    result = export_sheet(project, tmp_path / "export")

    with Image.open(result["sheet"]) as sheet:
        bbox = _alpha_bbox(sheet.crop((0, 0, 352, 352)))
        assert bbox is not None
        assert bbox[3] == 320

    metadata = json.loads(result["metadata"].read_text(encoding="utf-8"))
    assert metadata["frames"][0]["normalization"]["foot_y"] == 320
    assert metadata["frames"][0]["normalization"]["baseline_y"] == 320


def test_export_does_not_shrink_group_for_overwide_frames_and_records_clipping(tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    normal = _write_character_frame(frames_dir / "normal.png", "normal", 0, bbox=(108, 20, 148, 119))
    wide = _write_character_frame(frames_dir / "wide.png", "wide", 1, bbox=(0, 20, 255, 119))
    project = _project(tmp_path, [normal, wide])

    result = export_sheet(project, tmp_path / "export")

    metadata = json.loads(result["metadata"].read_text(encoding="utf-8"))
    assert metadata["scale_policy"]["scale"] == pytest.approx(2.0)
    assert metadata["scale_policy"]["width_constraint_enabled"] is False
    assert metadata["frames"][1]["normalization"]["scaled_bbox"]["width"] > 352
    assert metadata["frames"][1]["normalization"]["overflow"]["left"] is True
    assert metadata["frames"][1]["normalization"]["overflow"]["right"] is True
    assert metadata["frames"][1]["normalization"]["clipped"] is True


def test_export_preserves_semi_transparent_source_pixels(tmp_path):
    frame_path = tmp_path / "frame_000000.png"
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    for y in range(20, 120):
        for x in range(108, 148):
            image.putpixel((x, y), (255, 0, 0, 128))
    image.save(frame_path)
    project = _project(
        tmp_path,
        [
            FrameRecord(
                id="frame_000000",
                source_frame=0,
                raw_path=str(frame_path),
            )
        ],
    )

    result = export_sheet(project, tmp_path / "export")

    with Image.open(result["sheet"]) as sheet:
        alpha_histogram = sheet.crop((0, 0, 256, 256)).getchannel("A").histogram()
        assert alpha_histogram[128] > 0


def test_export_resolves_relative_frame_paths_against_project_root(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    frame_path = project_root / "frames" / "raw" / "frame_000000.png"
    frame_path.parent.mkdir(parents=True)
    _draw_character_image(frame_path)
    project = _project(
        project_root,
        [
            FrameRecord(
                id="frame_000000",
                source_frame=0,
                raw_path="frames/raw/frame_000000.png",
            )
        ],
    )
    other_cwd = tmp_path / "other-cwd"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    result = export_sheet(project, tmp_path / "export")

    assert result["sheet"].exists()


def test_export_rejects_columns_above_six():
    with pytest.raises(ValueError):
        ExportConfig(columns=7)

    with pytest.raises(ValueError):
        ExportConfig(max_columns=7)


def _project(
    tmp_path: Path,
    frames: list[FrameRecord],
    export: ExportConfig | None = None,
) -> ProjectConfig:
    return ProjectConfig(
        name="test-project",
        root=tmp_path,
        anchor=AnchorConfig(preset="center", x=0.5, y=0.5),
        export=export or ExportConfig(fps=8),
        frames=frames,
    )


def _write_character_frame(
    path: Path,
    frame_id: str,
    source_frame: int,
    bbox: tuple[int, int, int, int] = (108, 20, 148, 119),
    color: tuple[int, int, int, int] = (255, 0, 0, 255),
    enabled: bool = True,
) -> FrameRecord:
    _draw_character_image(path, bbox=bbox, color=color)
    return FrameRecord(
        id=frame_id,
        source_frame=source_frame,
        raw_path=str(path),
        enabled=enabled,
    )


def _draw_character_image(
    path: Path,
    bbox: tuple[int, int, int, int] = (108, 20, 148, 119),
    color: tuple[int, int, int, int] = (255, 0, 0, 255),
) -> None:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    x0, y0, x1, y1 = bbox
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            image.putpixel((x, y), color)
    image.save(path)


def _alpha_bbox(image: Image.Image, threshold: int = 20) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value > threshold else 0).getbbox()
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    return left, top, right - 1, bottom - 1
