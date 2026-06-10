from pathlib import Path
import re

from app.core.models import ProjectConfig
from app.core.paths import PROJECT_DIRS, project_file


SAFE_PROJECT_NAME = re.compile(r"^[A-Za-z0-9 _-]+$")


def create_project(projects_root: Path, name: str) -> ProjectConfig:
    project_root = _project_root_for_name(projects_root, name)
    if project_root.exists() or project_file(project_root).exists():
        raise FileExistsError(f"项目已存在：{name}")

    projects_root.mkdir(parents=True, exist_ok=True)
    project_root.mkdir()
    for project_dir in PROJECT_DIRS:
        (project_root / project_dir).mkdir(parents=True, exist_ok=True)

    project = ProjectConfig(name=name, root=project_root)
    save_project(project)
    return project


def save_project(project: ProjectConfig) -> None:
    project.root.mkdir(parents=True, exist_ok=True)
    project_file(project.root).write_text(
        project.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_project(project_root: Path) -> ProjectConfig:
    return ProjectConfig.model_validate_json(
        project_file(project_root).read_text(encoding="utf-8")
    )


def _project_root_for_name(projects_root: Path, name: str) -> Path:
    if name != name.strip() or not name:
        raise ValueError("项目名称不能为空，且首尾不能包含空白字符。")
    if not SAFE_PROJECT_NAME.fullmatch(name):
        raise ValueError("项目名称只能包含字母、数字、空格、下划线和连字符。")

    resolved_root = projects_root.resolve()
    project_root = (projects_root / name).resolve()
    try:
        project_root.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("项目名称不能指向项目目录外。") from exc
    return project_root
