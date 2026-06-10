"""Apply chroma keying to a list of frames."""

from pathlib import Path

from PIL import Image

from app.core.models import BackgroundKey, FrameRecord
from app.services.chroma_key import apply_chroma_key


def key_frames(
    frames: list[FrameRecord],
    output_dir: Path,
    raw_dir: Path,
    background: BackgroundKey,
    only_missing: bool = False,
) -> bool:
    """Run chroma keying on every enabled frame.

    Returns ``True`` if any frame was (re-)keyed.
    """
    keyed_dir = output_dir / "keyed"
    keyed_dir.mkdir(parents=True, exist_ok=True)
    changed = False

    for frame in frames:
        if not frame.enabled:
            continue

        keyed_path = keyed_dir / f"{frame.id}.png"
        if only_missing and frame.keyed_path and Path(frame.keyed_path).is_file():
            continue

        raw_path = raw_dir / f"{frame.id}.png"
        if not raw_path.is_file():
            raw_path = Path(frame.raw_path)

        with Image.open(raw_path) as image:
            keyed = apply_chroma_key(
                image,
                key_color=background.color,
                tolerance=background.tolerance,
                spill_suppression=max(background.spill_suppression, 0.75),
                edge_cleanup=background.edge_feather,
            )
            keyed.save(keyed_path)

        frame.keyed_path = str(keyed_path)
        changed = True

    return changed


def needs_keyed_frames(frames: list[FrameRecord]) -> bool:
    """Return ``True`` if any enabled frame is missing its keyed file."""
    for frame in frames:
        if not frame.enabled:
            continue
        if not frame.keyed_path:
            return True
        if not Path(frame.keyed_path).is_file():
            return True
    return False
