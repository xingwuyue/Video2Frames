"""Unified API routes — no project system, just import → process → export."""

from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Body, Request
from fastapi.responses import FileResponse

from app.core.models import ExportConfig, SessionState
from app.core.paths import ensure_output_dirs, output_dir_for_video
from app.services.frame_extract import extract_frames
from app.services.keying import key_frames
from app.services.sheet_export import export_sheet


router = APIRouter(prefix="/api", tags=["main"])
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session(request: Request) -> SessionState:
    return request.app.state.session


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
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        async for chunk in request.stream():
            if chunk:
                output.write(chunk)
    if destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        raise ValueError("视频文件为空。")


def _validated_file_path(output_dir: Path, relative_path: str) -> Path:
    """Resolve *relative_path* under *output_dir* and ensure it stays inside."""
    candidate = (output_dir / relative_path).resolve()
    try:
        candidate.relative_to(output_dir.resolve())
    except ValueError as exc:
        raise ValueError("文件路径不能指向输出目录外。") from exc
    return candidate


# ---------------------------------------------------------------------------
# POST /api/import  —  Import a video, extract frames, key & export
# ---------------------------------------------------------------------------

@router.post("/import")
async def import_video_route(request: Request) -> SessionState:
    session = _session(request)
    filename = _safe_video_filename(request.headers.get("x-filename"))
    sample_interval = _sample_interval(request, session.sample_every_n_frames)

    # Save video to a temporary location inside the workspace
    upload_dir = Path(request.app.state.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    video_path = upload_dir / filename
    await _write_request_body(request, video_path)

    # Output directory: alongside the video, named after the video stem
    output_dir = output_dir_for_video(video_path)
    ensure_output_dirs(output_dir)

    raw_dir = output_dir / "raw"
    # Extract frames
    frame_records = extract_frames(video_path, raw_dir, every_n=sample_interval)

    # Update session state
    session.video_path = str(video_path)
    session.video_name = video_path.stem
    session.output_dir = output_dir
    session.sample_every_n_frames = sample_interval
    session.frames = frame_records

    # Apply chroma keying
    key_frames(
        session.frames,
        output_dir,
        raw_dir,
        session.background,
    )

    # Export sprite sheet
    export_sheet(
        session.frames,
        session.export,
        session.anchor,
        session.sample_every_n_frames,
        output_dir,
    )

    return session


# ---------------------------------------------------------------------------
# POST /api/process/key  —  Re-run chroma keying with current settings
# ---------------------------------------------------------------------------

@router.post("/process/key")
def process_key_route(request: Request) -> SessionState:
    session = _session(request)
    if not session.output_dir or not session.frames:
        raise ValueError("请先导入视频。")

    raw_dir = session.output_dir / "raw"
    key_frames(
        session.frames,
        session.output_dir,
        raw_dir,
        session.background,
    )

    # Re-export after re-keying
    export_sheet(
        session.frames,
        session.export,
        session.anchor,
        session.sample_every_n_frames,
        session.output_dir,
    )

    return session


# ---------------------------------------------------------------------------
# POST /api/export  —  Re-export with updated export settings
# ---------------------------------------------------------------------------

@router.post("/export")
def export_route(
    request: Request,
    export_config: ExportConfig | None = Body(default=None),
) -> dict[str, str]:
    session = _session(request)
    if not session.output_dir or not session.frames:
        raise ValueError("请先导入视频。")

    if export_config is not None:
        session.export = export_config

    result = export_sheet(
        session.frames,
        session.export,
        session.anchor,
        session.sample_every_n_frames,
        session.output_dir,
    )
    return {key: str(path) for key, path in result.items()}


# ---------------------------------------------------------------------------
# GET /api/state  —  Return current session state
# ---------------------------------------------------------------------------

@router.get("/state")
def get_state_route(request: Request) -> SessionState:
    return _session(request)


# ---------------------------------------------------------------------------
# GET /api/files/{file_path}  —  Serve a file from the output directory
# ---------------------------------------------------------------------------

@router.get("/files/{file_path:path}")
def get_file_route(file_path: str, request: Request) -> FileResponse:
    session = _session(request)
    if not session.output_dir:
        raise LookupError("请先导入视频。")
    path = _validated_file_path(session.output_dir, file_path)
    if not path.is_file():
        raise LookupError("文件不存在。")
    return FileResponse(path)
