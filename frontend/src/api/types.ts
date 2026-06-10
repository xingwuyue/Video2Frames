export type BackgroundKeyMode = "green" | "red_purple" | "blue" | "white" | "custom" | string;

export interface BackgroundKey {
  mode: BackgroundKeyMode;
  color: [number, number, number];
  tolerance: number;
  edge_feather: number;
  spill_suppression: number;
}

export interface AnchorConfig {
  preset: "foot_center" | "center" | "top_center" | "custom" | string;
  x: number;
  y: number;
  frame_offsets: Record<string, [number, number]>;
}

export interface ExportConfig {
  cell_width: number;
  cell_height: number;
  rows: number;
  columns: number;
  auto_layout: boolean;
  max_columns: number;
  fps: number;
  include_frames: boolean;
  include_godot_helper: boolean;
  center_x: number;
  baseline_y: number;
  target_body_height: number;
  height_top_y: number;
  alpha_threshold: number;
  min_pixels_per_row: number;
  soft_width_limit: number;
  shared_scale_enabled: boolean;
  per_frame_scale_enabled: boolean;
  width_constraint_enabled: boolean;
}

export interface FrameRecord {
  id: string;
  source_frame: number;
  raw_path: string;
  keyed_path: string | null;
  enabled: boolean;
}

export interface ProjectConfig {
  name: string;
  root: string;
  source_video: string | null;
  source_fps: number | null;
  source_width: number | null;
  source_height: number | null;
  sample_every_n_frames: number;
  background: BackgroundKey;
  anchor: AnchorConfig;
  export: ExportConfig;
  frames: FrameRecord[];
}

export interface ExportResult {
  sheet: string;
  metadata: string;
}
