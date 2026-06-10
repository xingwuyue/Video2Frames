from pathlib import Path


OUTPUT_SUBDIRS = ("raw", "keyed", "exports")


def ensure_output_dirs(output_dir: Path) -> None:
    """Create the standard sub-directories inside *output_dir*."""
    for name in OUTPUT_SUBDIRS:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def output_dir_for_video(video_path: Path) -> Path:
    """Return ``<video_parent>/<video_stem>/`` as the output root."""
    return video_path.parent / video_path.stem
