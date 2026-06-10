import json
import math
from pathlib import Path
from statistics import median

from PIL import Image

from app.core.models import AnchorConfig, ExportConfig, FrameRecord


def export_sheet(
    frames: list[FrameRecord],
    export: ExportConfig,
    anchor: AnchorConfig,
    sample_every_n_frames: int,
    output_dir: Path,
) -> dict[str, Path]:
    """Build a sprite-sheet and write it alongside its JSON metadata.

    Parameters
    ----------
    frames : list[FrameRecord]
        Only *enabled* frames will be included.
    export : ExportConfig
    anchor : AnchorConfig
    sample_every_n_frames : int
    output_dir : Path
        The root output directory; files are written to ``output_dir/exports/``.
    """
    enabled_frames = [frame for frame in frames if frame.enabled]
    columns, rows = _layout(len(enabled_frames), export)
    capacity = rows * columns
    if len(enabled_frames) > capacity:
        raise ValueError("帧数超过当前表格容量。")

    exports_dir = output_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = exports_dir / "sheet.png"
    metadata_path = exports_dir / "frames.json"

    source_frames = _load_frames(enabled_frames)
    source_bboxes = [_alpha_bbox(image, export.alpha_threshold) for image in source_frames]
    heights = [bbox["height"] for bbox in source_bboxes if bbox is not None and bbox["height"] > 0]
    reference_height = median(heights) if heights else export.target_body_height
    shared_scale = export.target_body_height / reference_height if reference_height else 1.0

    sheet = Image.new(
        "RGBA",
        (columns * export.cell_width, rows * export.cell_height),
        (0, 0, 0, 0),
    )
    frame_metadata = []

    for index, (frame, rgba_frame, source_bbox) in enumerate(zip(enabled_frames, source_frames, source_bboxes)):
        row = index // columns
        column = index % columns
        x = column * export.cell_width
        y = row * export.cell_height
        normalized_frame, normalization = _normalize_frame(rgba_frame, source_bbox, export, shared_scale)
        sheet.paste(normalized_frame, (x, y))

        frame_metadata.append(
            {
                "id": frame.id,
                "source_frame": frame.source_frame,
                "x": x,
                "y": y,
                "w": export.cell_width,
                "h": export.cell_height,
                "anchor": {
                    "preset": anchor.preset,
                    "x": anchor.x,
                    "y": anchor.y,
                },
                "normalization": normalization,
            }
        )

    sheet.save(sheet_path)
    metadata_path.write_text(
        json.dumps(
            {
                "sheet": sheet_path.name,
                "version": "v2_height_fixed_baseline",
                "cell_width": export.cell_width,
                "cell_height": export.cell_height,
                "rows": rows,
                "columns": columns,
                "frame_count": len(enabled_frames),
                "fps": export.fps,
                "sampling": {
                    "take_every_n_frames": sample_every_n_frames,
                    "start_frame": 0,
                },
                "scale_policy": {
                    "mode": "fixed_height_shared_scale",
                    "target_body_height": export.target_body_height,
                    "reference_height": _json_number(reference_height),
                    "scale": shared_scale,
                    "shared_scale_enabled": True,
                    "width_constraint_enabled": False,
                    "per_frame_scale_enabled": False,
                },
                "alignment": {
                    "horizontal": "bbox_center_fallback",
                    "center_x": export.center_x,
                    "vertical": "foot_baseline",
                    "baseline_y": export.baseline_y,
                },
                "height_region": {
                    "top_y": export.height_top_y,
                    "bottom_y": export.baseline_y,
                    "height": export.target_body_height,
                },
                "pivot": {
                    "x": export.center_x,
                    "y": export.baseline_y,
                },
                "oversize_policy": {
                    "allow_width_variation": True,
                    "soft_width_limit": export.soft_width_limit,
                    "hard_canvas_width": export.cell_width,
                    "recommended_action_when_overflow": "inspect_or_split_effect_layer",
                },
                "frames": frame_metadata,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {"sheet": sheet_path, "metadata": metadata_path}


def _layout(frame_count: int, export) -> tuple[int, int]:
    if export.auto_layout:
        columns = min(frame_count, export.max_columns) if frame_count else export.max_columns
        rows = math.ceil(frame_count / export.max_columns) if frame_count else 1
        return columns, rows
    return export.columns, export.rows


def _load_frames(frames: list[FrameRecord]) -> list[Image.Image]:
    images = []
    for frame in frames:
        path = Path(frame.keyed_path or frame.raw_path)
        with Image.open(path) as source:
            images.append(source.convert("RGBA"))
    return images


def _normalize_frame(source: Image.Image, source_bbox: dict | None, export, scale: float) -> tuple[Image.Image, dict]:
    canvas = Image.new("RGBA", (export.cell_width, export.cell_height), (0, 0, 0, 0))
    if source_bbox is None:
        return canvas, {
            "source_bbox": None,
            "scaled_bbox": None,
            "normalized_bbox": None,
            "scale": scale,
            "foot_y": None,
            "baseline_y": export.baseline_y,
            "horizontal_reference": "bbox_center_fallback",
            "overflow": _overflow_flags(0, 0, 0, 0, export),
            "clipped": False,
        }

    scaled_size = (
        max(1, round(source.width * scale)),
        max(1, round(source.height * scale)),
    )
    scaled = source.resize(scaled_size, Image.Resampling.NEAREST)
    scaled_bbox = _alpha_bbox(scaled, export.alpha_threshold)
    if scaled_bbox is None:
        return canvas, {
            "source_bbox": source_bbox,
            "scaled_bbox": None,
            "normalized_bbox": None,
            "scale": scale,
            "foot_y": None,
            "baseline_y": export.baseline_y,
            "horizontal_reference": "bbox_center_fallback",
            "overflow": _overflow_flags(0, 0, 0, 0, export),
            "clipped": False,
        }

    foot_y = _detect_foot_y(scaled, scaled_bbox, export.alpha_threshold, export.min_pixels_per_row)
    horizontal_center = (scaled_bbox["left"] + scaled_bbox["right"] - 1) / 2
    paste_x = round(export.center_x - horizontal_center)
    paste_y = round(export.baseline_y - foot_y)
    _paste_clipped(canvas, scaled, paste_x, paste_y)

    normalized_bbox = _translate_bbox(scaled_bbox, paste_x, paste_y)
    overflow = _overflow_flags(
        normalized_bbox["left"],
        normalized_bbox["top"],
        normalized_bbox["right"],
        normalized_bbox["bottom"],
        export,
    )
    visible_bbox = _alpha_bbox(canvas, export.alpha_threshold)

    return canvas, {
        "source_bbox": source_bbox,
        "scaled_bbox": scaled_bbox,
        "normalized_bbox": visible_bbox,
        "scale": scale,
        "foot_y": export.baseline_y,
        "source_foot_y": foot_y,
        "baseline_y": export.baseline_y,
        "horizontal_reference": "bbox_center_fallback",
        "horizontal_fallback": "effective_bbox_center",
        "paste_offset": {"x": paste_x, "y": paste_y},
        "overflow": overflow,
        "clipped": any(overflow.values()),
    }


def _paste_clipped(canvas: Image.Image, image: Image.Image, paste_x: int, paste_y: int) -> None:
    left = max(0, paste_x)
    top = max(0, paste_y)
    right = min(canvas.width, paste_x + image.width)
    bottom = min(canvas.height, paste_y + image.height)
    if left >= right or top >= bottom:
        return

    source_left = left - paste_x
    source_top = top - paste_y
    source_right = source_left + (right - left)
    source_bottom = source_top + (bottom - top)
    canvas.paste(image.crop((source_left, source_top, source_right, source_bottom)), (left, top))


def _detect_foot_y(image: Image.Image, bbox: dict, alpha_threshold: int, min_pixels_per_row: int) -> int:
    alpha = image.getchannel("A")
    start_y = bbox["top"] + bbox["height"] // 2
    for y in range(bbox["bottom"] - 1, start_y - 1, -1):
        pixels = 0
        for x in range(bbox["left"], bbox["right"]):
            if alpha.getpixel((x, y)) > alpha_threshold:
                pixels += 1
        if pixels >= min_pixels_per_row:
            return y
    return bbox["bottom"] - 1


def _alpha_bbox(image: Image.Image, threshold: int) -> dict | None:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value > threshold else 0).getbbox()
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left,
        "height": bottom - top,
    }


def _translate_bbox(bbox: dict, x: int, y: int) -> dict:
    return {
        "left": bbox["left"] + x,
        "top": bbox["top"] + y,
        "right": bbox["right"] + x,
        "bottom": bbox["bottom"] + y,
        "width": bbox["width"],
        "height": bbox["height"],
    }


def _overflow_flags(left: int, top: int, right: int, bottom: int, export) -> dict[str, bool]:
    return {
        "left": left < 0,
        "top": top < 0,
        "right": right > export.cell_width,
        "bottom": bottom > export.cell_height,
        "soft_width": (right - left) > export.soft_width_limit,
    }


def _json_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else value
