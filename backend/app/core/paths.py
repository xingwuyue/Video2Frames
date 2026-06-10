from pathlib import Path


PROJECT_FILE = "project.json"
PROJECT_DIRS = (
    Path("source"),
    Path("frames") / "raw",
    Path("frames") / "keyed",
    Path("edits"),
    Path("exports"),
)


def project_file(project_root: Path) -> Path:
    return project_root / PROJECT_FILE
