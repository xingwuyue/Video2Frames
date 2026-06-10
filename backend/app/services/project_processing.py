from pathlib import Path

from PIL import Image

from app.core.models import ProjectConfig
from app.services.chroma_key import apply_chroma_key


def key_project_frames(project: ProjectConfig, keyed_dir: Path, only_missing: bool = False) -> bool:
    keyed_dir.mkdir(parents=True, exist_ok=True)
    changed = False

    for frame in project.frames:
        if not frame.enabled:
            continue

        keyed_path = keyed_dir / f"{frame.id}.png"
        if only_missing and frame.keyed_path and (project.root / frame.keyed_path).is_file():
            continue

        raw_path = _project_frame_path(project.root, frame.raw_path)
        with Image.open(raw_path) as image:
            keyed = apply_chroma_key(
                image,
                key_color=project.background.color,
                tolerance=project.background.tolerance,
                spill_suppression=max(project.background.spill_suppression, 0.75),
                edge_cleanup=project.background.edge_feather,
            )
            keyed.save(keyed_path)

        next_keyed_path = keyed_path.relative_to(project.root).as_posix()
        if frame.keyed_path != next_keyed_path:
            frame.keyed_path = next_keyed_path
            changed = True

    return changed


def project_needs_keyed_frames(project: ProjectConfig) -> bool:
    for frame in project.frames:
        if not frame.enabled:
            continue
        if not frame.keyed_path:
            return True
        if not _project_frame_path(project.root, frame.keyed_path).is_file():
            return True
    return False


def _project_frame_path(project_root: Path, frame_path: str) -> Path:
    path = Path(frame_path)
    resolved_root = project_root.resolve()
    candidate = path.resolve() if path.is_absolute() else (project_root / path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("帧路径不能指向项目目录外。") from exc
    return candidate
