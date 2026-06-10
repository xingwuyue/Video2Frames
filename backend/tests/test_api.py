import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.models import ExportConfig, FrameRecord
from app.core.project_store import create_project, load_project, save_project
from app.main import create_app


def test_post_projects_creates_project(tmp_path):
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post("/api/projects", json={"name": "walk"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "walk"
    assert payload["root"] == str(tmp_path / "walk")
    assert (tmp_path / "walk" / "project.json").exists()


def test_get_project_returns_saved_config(tmp_path):
    project = create_project(tmp_path, "walk")
    project.export.rows = 3
    save_project(project)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.get("/api/projects/walk")

    assert response.status_code == 200
    assert response.json()["export"]["rows"] == 3


def test_get_project_auto_keys_legacy_raw_frames_and_exports_sheet(tmp_path):
    project = create_project(tmp_path, "legacy")
    raw_frame = project.root / "frames" / "raw" / "frame_000000.png"
    Image.new("RGBA", (2, 1), (0, 255, 0, 255)).save(raw_frame)
    image = Image.open(raw_frame)
    image.putpixel((1, 0), (255, 0, 0, 255))
    image.save(raw_frame)
    project.export = ExportConfig(cell_width=2, cell_height=2, rows=1, columns=1, auto_layout=False)
    project.frames = [
        FrameRecord(
            id="frame_000000",
            source_frame=0,
            raw_path="frames/raw/frame_000000.png",
        )
    ]
    save_project(project)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.get("/api/projects/legacy")

    assert response.status_code == 200
    frame = response.json()["frames"][0]
    assert frame["keyed_path"] == "frames/keyed/frame_000000.png"
    assert (project.root / "frames" / "keyed" / "frame_000000.png").exists()
    assert (project.root / "exports" / "sheet.png").exists()
    with Image.open(project.root / "frames" / "keyed" / "frame_000000.png") as keyed:
        assert keyed.getpixel((0, 0)) == (0, 255, 0, 0)
        assert keyed.getpixel((1, 0)) == (255, 0, 0, 255)


def test_get_project_file_serves_frame_inside_project(tmp_path):
    project = create_project(tmp_path, "walk")
    frame_path = project.root / "frames" / "raw" / "frame_000000.png"
    Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(frame_path)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.get("/api/projects/walk/files/frames/raw/frame_000000.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == frame_path.read_bytes()


def test_get_project_file_rejects_paths_outside_project(tmp_path):
    create_project(tmp_path, "walk")
    outside_file = tmp_path / "outside.png"
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(outside_file)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.get("/api/projects/walk/files/../outside.png")

    assert response.status_code in {400, 404}
    assert response.content != outside_file.read_bytes()


def test_api_allows_local_frontend_cors_preflight(tmp_path):
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.options(
        "/api/projects",
        headers={
            "origin": "http://127.0.0.1:5173",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_import_video_saves_source_keys_frames_and_exports_default_sheet(tmp_path, tiny_test_video):
    project = create_project(tmp_path, "walk")
    stale_keyed = project.root / "frames" / "keyed" / "frame_000000.png"
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(stale_keyed)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post(
        "/api/projects/walk/import/video",
        content=tiny_test_video.read_bytes(),
        headers={
            "content-type": "video/mp4",
            "x-filename": "desktop-walk.mp4",
            "x-sample-every-n-frames": "2",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_video"] == "source/desktop-walk.mp4"
    assert payload["sample_every_n_frames"] == 2
    assert len(payload["frames"]) == 3
    assert payload["frames"][0]["raw_path"] == "frames/raw/frame_000000.png"
    assert payload["frames"][0]["keyed_path"] == "frames/keyed/frame_000000.png"
    assert (project.root / "source" / "desktop-walk.mp4").exists()
    assert (project.root / "frames" / "raw" / "frame_000000.png").exists()
    assert (project.root / "frames" / "keyed" / "frame_000000.png").exists()
    with Image.open(stale_keyed) as replaced_keyed:
        assert replaced_keyed.size != (1, 1)
    assert (project.root / "exports" / "sheet.png").exists()
    assert (project.root / "exports" / "frames.json").exists()
    saved = load_project(project.root)
    assert saved.source_video == "source/desktop-walk.mp4"
    assert len(saved.frames) == 3
    assert saved.frames[0].keyed_path == "frames/keyed/frame_000000.png"


def test_import_video_rejects_unsupported_file_type(tmp_path, tiny_test_video):
    create_project(tmp_path, "walk")
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post(
        "/api/projects/walk/import/video",
        content=tiny_test_video.read_bytes(),
        headers={"x-filename": "notes.txt"},
    )

    assert response.status_code == 400
    assert "视频格式" in response.json()["error"]


def test_process_key_applies_chroma_key_to_cached_frames(tmp_path):
    project = create_project(tmp_path, "walk")
    raw_frame = project.root / "frames" / "raw" / "frame_000000.png"
    Image.new("RGBA", (2, 1), (0, 255, 0, 255)).save(raw_frame)
    image = Image.open(raw_frame)
    image.putpixel((1, 0), (255, 0, 0, 255))
    image.save(raw_frame)
    project.frames = [
        FrameRecord(
            id="frame_000000",
            source_frame=0,
            raw_path="frames/raw/frame_000000.png",
        )
    ]
    save_project(project)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post("/api/projects/walk/process/key")

    assert response.status_code == 200
    frame = response.json()["frames"][0]
    assert frame["keyed_path"] == "frames/keyed/frame_000000.png"
    keyed_path = project.root / frame["keyed_path"]
    with Image.open(keyed_path) as keyed:
        assert keyed.getpixel((0, 0)) == (0, 255, 0, 0)
        assert keyed.getpixel((1, 0)) == (255, 0, 0, 255)


def test_process_key_rejects_raw_frame_paths_outside_project(tmp_path):
    project = create_project(tmp_path, "walk")
    outside_frame = tmp_path / "outside.png"
    Image.new("RGBA", (1, 1), (0, 255, 0, 255)).save(outside_frame)
    project.frames = [
        FrameRecord(
            id="frame_000000",
            source_frame=0,
            raw_path=str(outside_frame),
        )
    ]
    save_project(project)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post("/api/projects/walk/process/key")

    assert response.status_code == 400
    assert response.json() == {"error": "帧路径不能指向项目目录外。"}


def test_process_key_normalizes_tampered_project_root(tmp_path):
    project = create_project(tmp_path, "walk")
    raw_frame = project.root / "frames" / "raw" / "frame_000000.png"
    Image.new("RGBA", (1, 1), (0, 255, 0, 255)).save(raw_frame)
    project.frames = [
        FrameRecord(
            id="frame_000000",
            source_frame=0,
            raw_path="frames/raw/frame_000000.png",
        )
    ]
    save_project(project)
    outside_root = tmp_path / "outside-project"
    outside_root.mkdir()
    project_json = project.root / "project.json"
    config = json.loads(project_json.read_text(encoding="utf-8"))
    config["root"] = str(outside_root)
    project_json.write_text(json.dumps(config), encoding="utf-8")
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post("/api/projects/walk/process/key")

    assert response.status_code == 200
    frame = response.json()["frames"][0]
    assert response.json()["root"] == str(project.root.resolve())
    assert frame["keyed_path"] == "frames/keyed/frame_000000.png"
    assert (project.root / "frames" / "keyed" / "frame_000000.png").exists()
    assert not (outside_root / "frames" / "keyed" / "frame_000000.png").exists()


def test_process_key_rejects_keyed_output_directory_symlink_escape(tmp_path):
    project = create_project(tmp_path, "walk")
    raw_frame = project.root / "frames" / "raw" / "frame_000000.png"
    Image.new("RGBA", (1, 1), (0, 255, 0, 255)).save(raw_frame)
    project.frames = [
        FrameRecord(
            id="frame_000000",
            source_frame=0,
            raw_path="frames/raw/frame_000000.png",
        )
    ]
    save_project(project)
    outside_output = tmp_path / "outside-keyed"
    outside_output.mkdir()
    _replace_with_directory_symlink(project.root / "frames" / "keyed", outside_output)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post("/api/projects/walk/process/key")

    assert response.status_code == 400
    assert response.json() == {"error": "项目输出路径不能指向项目目录外。"}
    assert not (outside_output / "frame_000000.png").exists()


def test_export_writes_sheet_and_frames_json(tmp_path):
    project = create_project(tmp_path, "walk")
    raw_frame = project.root / "frames" / "raw" / "frame_000000.png"
    Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(raw_frame)
    project.export = ExportConfig(cell_width=2, cell_height=2, rows=1, columns=1, auto_layout=False)
    project.frames = [
        FrameRecord(
            id="frame_000000",
            source_frame=0,
            raw_path="frames/raw/frame_000000.png",
        )
    ]
    save_project(project)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post("/api/projects/walk/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "sheet": str(project.root / "exports" / "sheet.png"),
        "metadata": str(project.root / "exports" / "frames.json"),
    }
    assert (project.root / "exports" / "sheet.png").exists()
    metadata = json.loads((project.root / "exports" / "frames.json").read_text(encoding="utf-8"))
    assert metadata["frame_count"] == 1


def test_export_uses_request_export_config_without_saving_project(tmp_path):
    project = create_project(tmp_path, "walk")
    project.export = ExportConfig(cell_width=16, cell_height=16, rows=1, columns=1, auto_layout=False)
    raw_frame = project.root / "frames" / "raw" / "frame_000000.png"
    Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(raw_frame)
    project.frames = [
        FrameRecord(
            id="frame_000000",
            source_frame=0,
            raw_path="frames/raw/frame_000000.png",
        )
    ]
    save_project(project)
    client = TestClient(create_app(projects_root=tmp_path))

    request_config = project.export.model_copy(
        update={
            "cell_width": 32,
            "cell_height": 32,
            "auto_layout": True,
            "max_columns": 6,
            "center_x": 16,
            "baseline_y": 28,
            "target_body_height": 24,
            "height_top_y": 4,
        }
    ).model_dump()

    response = client.post("/api/projects/walk/export", json=request_config)

    assert response.status_code == 200
    metadata = json.loads((project.root / "exports" / "frames.json").read_text(encoding="utf-8"))
    assert metadata["cell_width"] == 32
    assert metadata["cell_height"] == 32
    assert metadata["columns"] == 1
    assert metadata["alignment"]["center_x"] == 16
    assert metadata["alignment"]["baseline_y"] == 28
    assert metadata["height_region"] == {"top_y": 4, "bottom_y": 28, "height": 24}
    assert metadata["scale_policy"]["shared_scale_enabled"] is True
    assert metadata["scale_policy"]["per_frame_scale_enabled"] is False
    assert metadata["scale_policy"]["width_constraint_enabled"] is False
    assert load_project(project.root).export.cell_width == 16


def test_export_rejects_frame_paths_outside_project(tmp_path):
    project = create_project(tmp_path, "walk")
    outside_frame = tmp_path / "outside.png"
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(outside_frame)
    project.export = ExportConfig(cell_width=1, cell_height=1, rows=1, columns=1)
    project.frames = [
        FrameRecord(
            id="frame_000000",
            source_frame=0,
            raw_path=str(outside_frame),
        )
    ]
    save_project(project)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post("/api/projects/walk/export")

    assert response.status_code == 400
    assert response.json() == {"error": "帧路径不能指向项目目录外。"}
    assert not (project.root / "exports" / "sheet.png").exists()


def test_export_rejects_output_directory_symlink_escape(tmp_path):
    project = create_project(tmp_path, "walk")
    raw_frame = project.root / "frames" / "raw" / "frame_000000.png"
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(raw_frame)
    project.export = ExportConfig(cell_width=1, cell_height=1, rows=1, columns=1)
    project.frames = [
        FrameRecord(
            id="frame_000000",
            source_frame=0,
            raw_path="frames/raw/frame_000000.png",
        )
    ]
    save_project(project)
    outside_output = tmp_path / "outside-exports"
    outside_output.mkdir()
    _replace_with_directory_symlink(project.root / "exports", outside_output)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post("/api/projects/walk/export")

    assert response.status_code == 400
    assert response.json() == {"error": "项目输出路径不能指向项目目录外。"}
    assert not (outside_output / "sheet.png").exists()
    assert not (outside_output / "frames.json").exists()


def test_missing_project_returns_404_json_error(tmp_path):
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.get("/api/projects/missing")

    assert response.status_code == 404
    assert response.json() == {"error": "项目不存在。"}


def test_export_capacity_overflow_returns_400_json_error(tmp_path):
    project = create_project(tmp_path, "walk")
    project.export = ExportConfig(cell_width=2, cell_height=2, rows=1, columns=1, auto_layout=False)
    for index in range(2):
        raw_frame = project.root / "frames" / "raw" / f"frame_{index:06d}.png"
        Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(raw_frame)
        project.frames.append(
            FrameRecord(
                id=f"frame_{index:06d}",
                source_frame=index,
                raw_path=f"frames/raw/frame_{index:06d}.png",
            )
        )
    save_project(project)
    client = TestClient(create_app(projects_root=tmp_path))

    response = client.post("/api/projects/walk/export")

    assert response.status_code == 400
    assert response.json() == {"error": "帧数超过当前表格容量。"}


def _replace_with_directory_symlink(link_path, target_path):
    link_path.rmdir()
    try:
        link_path.symlink_to(target_path, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"Directory symlinks are not supported in this environment: {exc}")
