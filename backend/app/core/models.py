from pathlib import Path

from pydantic import BaseModel, Field


class BackgroundKey(BaseModel):
    mode: str = "green"
    color: tuple[int, int, int] = (0, 255, 0)
    tolerance: int = 45
    edge_feather: int = 1
    spill_suppression: float = 0.25


class AnchorConfig(BaseModel):
    preset: str = "foot_center"
    x: float = 0.5
    y: float = 1.0
    frame_offsets: dict[str, tuple[float, float]] = Field(default_factory=dict)


class ExportConfig(BaseModel):
    cell_width: int = Field(default=352, gt=0)
    cell_height: int = Field(default=352, gt=0)
    rows: int = Field(default=1, gt=0)
    columns: int = Field(default=6, gt=0, le=6)
    auto_layout: bool = True
    max_columns: int = Field(default=6, gt=0, le=6)
    fps: int = Field(default=12, gt=0)
    include_frames: bool = True
    include_godot_helper: bool = True
    center_x: int = 176
    baseline_y: int = 320
    target_body_height: int = Field(default=200, gt=0)
    height_top_y: int = 120
    alpha_threshold: int = Field(default=20, ge=0, le=255)
    min_pixels_per_row: int = Field(default=3, gt=0)
    soft_width_limit: int = Field(default=340, gt=0)
    shared_scale_enabled: bool = True
    per_frame_scale_enabled: bool = False
    width_constraint_enabled: bool = False


class FrameRecord(BaseModel):
    id: str
    source_frame: int
    raw_path: str
    keyed_path: str | None = None
    enabled: bool = True


class SessionState(BaseModel):
    """Runtime state for the current video import session.

    Unlike the old ProjectConfig this is NOT persisted to disk as a
    "project file".  The backend keeps a single instance in memory and
    the frontend drives it through the API.
    """
    video_path: str | None = None
    video_name: str | None = None
    output_dir: Path | None = None
    source_fps: float | None = None
    source_width: int | None = None
    source_height: int | None = None
    sample_every_n_frames: int = 3
    background: BackgroundKey = Field(default_factory=BackgroundKey)
    anchor: AnchorConfig = Field(default_factory=AnchorConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    frames: list[FrameRecord] = Field(default_factory=list)
