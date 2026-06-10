from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.models import ExportConfig
from app.core.project_store import create_project, load_project, save_project


def test_create_project_writes_project_json(tmp_path):
    project = create_project(tmp_path, "walk")
    assert project.name == "walk"
    assert (tmp_path / "walk" / "project.json").exists()


def test_create_project_creates_required_directories(tmp_path):
    create_project(tmp_path, "walk")

    assert (tmp_path / "walk" / "source").is_dir()
    assert (tmp_path / "walk" / "frames" / "raw").is_dir()
    assert (tmp_path / "walk" / "frames" / "keyed").is_dir()
    assert (tmp_path / "walk" / "edits").is_dir()
    assert (tmp_path / "walk" / "exports").is_dir()


@pytest.mark.parametrize(
    "name",
    [
        "..\\outside",
        "../outside",
        "a/b",
        "",
        "   ",
        str(Path.cwd().anchor) or "C:\\",
    ],
)
def test_create_project_rejects_invalid_names(tmp_path, name):
    with pytest.raises(ValueError):
        create_project(tmp_path, name)


def test_duplicate_create_project_raises_and_does_not_overwrite(tmp_path):
    project = create_project(tmp_path, "attack")
    project.anchor.preset = "custom"
    save_project(project)

    with pytest.raises(FileExistsError):
        create_project(tmp_path, "attack")

    loaded = load_project(tmp_path / "attack")
    assert loaded.anchor.preset == "custom"


def test_save_and_load_project_preserves_anchor_and_layout(tmp_path):
    project = create_project(tmp_path, "attack")
    project.anchor.preset = "foot_center"
    project.export.rows = 4
    project.export.columns = 3

    save_project(project)

    loaded = load_project(tmp_path / "attack")
    assert loaded.anchor.preset == "foot_center"
    assert loaded.export.rows == 4
    assert loaded.export.columns == 3


def test_save_and_load_project_preserves_path_and_tuple_types(tmp_path):
    project = create_project(tmp_path, "jump")
    project.background.color = (255, 0, 255)
    project.anchor.frame_offsets["f1"] = (1.25, -2.5)

    save_project(project)

    loaded = load_project(tmp_path / "jump")
    assert loaded.root == tmp_path / "jump"
    assert isinstance(loaded.root, Path)
    assert loaded.background.color == (255, 0, 255)
    assert isinstance(loaded.background.color, tuple)
    assert loaded.anchor.frame_offsets["f1"] == (1.25, -2.5)
    assert isinstance(loaded.anchor.frame_offsets["f1"], tuple)


@pytest.mark.parametrize("field", ["cell_width", "cell_height", "rows", "columns", "fps"])
@pytest.mark.parametrize("value", [0, -1])
def test_export_layout_fields_must_be_positive(field, value):
    with pytest.raises(ValidationError):
        ExportConfig(**{field: value})
