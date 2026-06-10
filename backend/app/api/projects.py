from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.models import ProjectConfig
from app.core.project_store import _project_root_for_name, create_project, load_project, save_project
from app.services.project_processing import key_project_frames, project_needs_keyed_frames
from app.services.sheet_export import export_sheet


router = APIRouter(prefix="/api/projects", tags=["projects"])
OUTPUT_PATH_ESCAPE_ERROR = "项目输出路径不能指向项目目录外。"


class CreateProjectRequest(BaseModel):
    name: str


def projects_root(request: Request) -> Path:
    return request.app.state.projects_root


def load_project_by_name(root: Path, name: str) -> ProjectConfig:
    project_root = _project_root_for_name(root, name)
    try:
        project = load_project(project_root)
    except FileNotFoundError as exc:
        raise LookupError("项目不存在。") from exc
    project.root = project_root.resolve()
    return project


def project_owned_path(project_root: Path, path: Path) -> Path:
    resolved_root = project_root.resolve()
    candidate = path.resolve() if path.is_absolute() else (project_root / path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("帧路径不能指向项目目录外。") from exc
    return candidate


def project_output_dir(project_root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else project_root / path
    _validate_project_output(project_root, candidate)
    candidate.mkdir(parents=True, exist_ok=True)
    _validate_project_output(project_root, candidate)
    return candidate


def project_output_path(project_root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else project_root / path
    _validate_project_output(project_root, candidate)
    return candidate


def _validate_project_output(project_root: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError(OUTPUT_PATH_ESCAPE_ERROR) from exc


@router.post("")
def create_project_route(body: CreateProjectRequest, request: Request) -> ProjectConfig:
    return create_project(projects_root(request), body.name)


@router.get("/{name}")
def get_project_route(name: str, request: Request) -> ProjectConfig:
    project = load_project_by_name(projects_root(request), name)
    if project_needs_keyed_frames(project):
        keyed_dir = project_output_dir(project.root, project.root / "frames" / "keyed")
        key_project_frames(project, keyed_dir, only_missing=True)
        export_dir = project_output_dir(project.root, project.root / "exports")
        export_sheet(project, export_dir)
        save_project(project)
    return project


@router.get("/{name}/files/{file_path:path}")
def get_project_file_route(name: str, file_path: str, request: Request) -> FileResponse:
    project = load_project_by_name(projects_root(request), name)
    path = project_owned_path(project.root, Path(file_path))
    if not path.is_file():
        raise LookupError("文件不存在。")
    return FileResponse(path)
