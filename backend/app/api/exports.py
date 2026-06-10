from pathlib import Path

from fastapi import APIRouter, Body, Request

from app.core.models import ExportConfig
from app.api.projects import (
    load_project_by_name,
    project_output_dir,
    project_output_path,
    project_owned_path,
    projects_root,
)
from app.services.sheet_export import export_sheet


router = APIRouter(prefix="/api/projects", tags=["exports"])


@router.post("/{name}/export")
def export_project_route(
    name: str,
    request: Request,
    export_config: ExportConfig | None = Body(default=None),
) -> dict[str, str]:
    project = load_project_by_name(projects_root(request), name)
    if export_config is not None:
        project.export = export_config
    for frame in project.frames:
        if frame.enabled:
            project_owned_path(project.root, Path(frame.keyed_path or frame.raw_path))
    export_dir = project_output_dir(project.root, project.root / "exports")
    project_output_path(project.root, export_dir / "sheet.png")
    project_output_path(project.root, export_dir / "frames.json")
    result = export_sheet(project, export_dir)
    return {key: str(path) for key, path in result.items()}
