from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Request
from app.api.projects import (
    load_project_by_name,
    project_output_dir,
    project_output_path,
    projects_root,
)
from app.core.models import ProjectConfig
from app.core.project_store import save_project
from app.services.frame_extract import extract_frames
from app.services.project_processing import key_project_frames
from app.services.sheet_export import export_sheet


router = APIRouter(prefix="/api/projects", tags=["processing"])
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}


@router.post("/{name}/import/video")
async def import_video_route(name: str, request: Request) -> ProjectConfig:
    project = load_project_by_name(projects_root(request), name)
    filename = _safe_video_filename(request.headers.get("x-filename"))
    sample_interval = _sample_interval(request, project.sample_every_n_frames)

    source_dir = project_output_dir(project.root, project.root / "source")
    source_path = project_output_path(project.root, source_dir / filename)
    await _write_request_body(request, source_path)

    raw_dir = project_output_dir(project.root, project.root / "frames" / "raw")
    keyed_dir = project_output_dir(project.root, project.root / "frames" / "keyed")
    frames = extract_frames(source_path, raw_dir, every_n=sample_interval)
    _clear_keyed_frames(keyed_dir)

    project.source_video = source_path.relative_to(project.root).as_posix()
    project.sample_every_n_frames = sample_interval
    project.frames = [_with_project_relative_raw_path(project.root, frame) for frame in frames]
    key_project_frames(project, keyed_dir)
    export_dir = project_output_dir(project.root, project.root / "exports")
    export_sheet(project, export_dir)
    save_project(project)
    return project


@router.post("/{name}/process/key")
def process_key_route(name: str, request: Request) -> ProjectConfig:
    project = load_project_by_name(projects_root(request), name)
    keyed_dir = project_output_dir(project.root, project.root / "frames" / "keyed")
    key_project_frames(project, keyed_dir)
    save_project(project)
    return project


def _safe_video_filename(filename_header: str | None) -> str:
    filename = Path(unquote(filename_header or "")).name
    if not filename:
        filename = "source-video.mp4"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_VIDEO_EXTENSIONS:
        supported = "、".join(sorted(SUPPORTED_VIDEO_EXTENSIONS))
        raise ValueError(f"视频格式不支持，请使用 {supported}。")
    return filename


def _sample_interval(request: Request, current_interval: int) -> int:
    header_value = request.headers.get("x-sample-every-n-frames")
    if header_value is None or not header_value.strip():
        return current_interval
    try:
        interval = int(header_value)
    except ValueError as exc:
        raise ValueError("抽帧间隔必须是正整数。") from exc
    if interval < 1:
        raise ValueError("抽帧间隔必须大于等于 1。")
    return interval


async def _write_request_body(request: Request, destination: Path) -> None:
    with destination.open("wb") as output:
        async for chunk in request.stream():
            if chunk:
                output.write(chunk)
    if destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        raise ValueError("视频文件为空。")


def _with_project_relative_raw_path(project_root: Path, frame):
    frame.raw_path = Path(frame.raw_path).relative_to(project_root).as_posix()
    frame.keyed_path = None
    return frame


def _clear_keyed_frames(keyed_dir: Path) -> None:
    for path in keyed_dir.glob("frame_*.png"):
        path.unlink()
