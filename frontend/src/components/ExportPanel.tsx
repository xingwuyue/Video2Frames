import { FileCode2, FolderOutput, Loader2, PackageCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { exportProject } from "../api/client";
import type { ExportConfig, ExportResult, SessionState } from "../api/types";

const capacityError = "帧数超过当前行列容量，请增加行列或删除帧。";

type ExportPanelProps = {
  session: SessionState | null;
  enabledFrameCount: number;
};

type CapacityInput = {
  auto_layout: boolean;
  rows: number;
  columns: number;
  enabledFrameCount: number;
};

type ResultPath = {
  label: string;
  value: string;
};

type GuardedExportInput = CapacityInput & {
  hasSession: boolean;
  config: Partial<ExportConfig>;
  exportProjectAction: (config?: Partial<ExportConfig>) => Promise<ExportResult>;
};

type GuardedExportResult =
  | {
      ok: true;
      result: ExportResult;
    }
  | {
      ok: false;
      error: string;
    };

export function validateExportCapacity({ auto_layout, rows, columns, enabledFrameCount }: CapacityInput): string | null {
  if (auto_layout) {
    return null;
  }
  return enabledFrameCount > rows * columns ? capacityError : null;
}

export async function runGuardedExport({
  hasSession,
  auto_layout,
  rows,
  columns,
  enabledFrameCount,
  config,
  exportProjectAction
}: GuardedExportInput): Promise<GuardedExportResult> {
  if (!hasSession) {
    return { ok: false, error: "请先导入视频。" };
  }

  const validationError = validateExportCapacity({ auto_layout, rows, columns, enabledFrameCount });
  if (validationError) {
    return { ok: false, error: validationError };
  }

  return { ok: true, result: await exportProjectAction(config) };
}

export function collectExportResultPaths(result: ExportResult | null): ResultPath[] {
  if (!result) {
    return [];
  }

  return [
    { label: "sheet.png", value: result.sheet },
    { label: "frames.json", value: result.metadata }
  ];
}

export function ExportPanel({ session, enabledFrameCount }: ExportPanelProps) {
  const [settings, setSettings] = useState<ExportConfig>(() => exportDefaults(session));
  const [result, setResult] = useState<ExportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setSettings(exportDefaults(session));
    setResult(null);
    setError(null);
  }, [session]);

  const capacity = settings.rows * settings.columns;
  const layoutSummary = settings.auto_layout
    ? `${enabledFrameCount} 帧，最多 ${settings.max_columns} 列，行数自动`
    : `${enabledFrameCount} / ${capacity}`;
  const validationError = validateExportCapacity({
    auto_layout: settings.auto_layout,
    rows: settings.rows,
    columns: settings.columns,
    enabledFrameCount
  });

  const resultPaths = useMemo(() => collectExportResultPaths(result), [result]);

  function updateNumber(
    field: keyof Pick<ExportConfig, "rows" | "columns" | "max_columns" | "cell_width" | "cell_height" | "fps">
  ) {
    return (value: string) => {
      const parsed = Number.parseInt(value, 10);
      const minimumValue = Number.isFinite(parsed) ? Math.max(1, parsed) : 1;
      const normalizedValue = field === "columns" || field === "max_columns" ? Math.min(6, minimumValue) : minimumValue;
      setSettings((current) => ({
        ...current,
        [field]: normalizedValue
      }));
    };
  }

  function updateBoolean(field: keyof Pick<ExportConfig, "auto_layout">) {
    return (checked: boolean) => {
      setSettings((current) => ({ ...current, [field]: checked }));
    };
  }

  async function handleExport() {
    setResult(null);
    setError(null);

    setLoading(true);
    try {
      const exported = await runGuardedExport({
        hasSession: Boolean(session?.video_name),
        auto_layout: settings.auto_layout,
        rows: settings.rows,
        columns: settings.columns,
        enabledFrameCount,
        config: createExportRequestConfig(settings),
        exportProjectAction: exportProject
      });

      if (exported.ok) {
        setResult(exported.result);
      } else {
        setError(exported.error);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "导出失败。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="export-panel-section" aria-label="Godot 导出设置">
      <PanelTitle icon={<FolderOutput size={17} aria-hidden="true" />} title="Godot 导出" />
      <p className="helper-text">默认按 352x352 单格、最多 6 列导出；后端会统一角色高度和脚底基线。</p>

      <div className="export-grid">
        {settings.auto_layout ? (
          <NumberField label="最多列数" value={settings.max_columns} max={6} onChange={updateNumber("max_columns")} />
        ) : (
          <>
            <NumberField label="行数" value={settings.rows} onChange={updateNumber("rows")} />
            <NumberField label="列数" value={settings.columns} max={6} onChange={updateNumber("columns")} />
          </>
        )}
        <NumberField label="格宽" value={settings.cell_width} onChange={updateNumber("cell_width")} />
        <NumberField label="格高" value={settings.cell_height} onChange={updateNumber("cell_height")} />
        <NumberField label="帧率" value={settings.fps} onChange={updateNumber("fps")} />
      </div>

      <div className="settings-stack compact-settings">
        <label className="toggle-control export-toggle">
          <input
            type="checkbox"
            checked={settings.auto_layout}
            onChange={(event) => updateBoolean("auto_layout")(event.target.checked)}
          />
          <span>自动行数布局</span>
        </label>
      </div>

      <div className="export-capacity" aria-live="polite">
        <span>{settings.auto_layout ? "布局" : "容量"}</span>
        <strong>{layoutSummary}</strong>
      </div>

      {validationError ? <div className="status-box status-error">{validationError}</div> : null}
      {error && error !== validationError ? <div className="status-box status-error">{error}</div> : null}

      <button
        type="button"
        className="primary-button full-width export-button"
        disabled={!session?.video_name || loading || Boolean(validationError)}
        onClick={handleExport}
      >
        {loading ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <PackageCheck size={16} aria-hidden="true" />}
        导出 Godot 文件
      </button>

      {resultPaths.length > 0 ? (
        <div className="export-results">
          <div className="panel-title result-title">
            <FileCode2 size={15} aria-hidden="true" />
            <h2>输出</h2>
          </div>
          {resultPaths.map((path) => (
            <div className="result-row" key={path.label}>
              <span>{path.label}</span>
              <code title={path.value}>{path.value}</code>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function NumberField({
  label,
  max,
  value,
  onChange
}: {
  label: string;
  max?: number;
  value: number;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" min={1} max={max} step={1} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="panel-title">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

export function createDefaultExportConfig(): ExportConfig {
  return {
    auto_layout: true,
    rows: 1,
    columns: 6,
    max_columns: 6,
    cell_width: 352,
    cell_height: 352,
    fps: 12,
    include_frames: true,
    include_godot_helper: true,
    center_x: 176,
    baseline_y: 320,
    target_body_height: 200,
    height_top_y: 120,
    alpha_threshold: 20,
    min_pixels_per_row: 3,
    soft_width_limit: 340,
    shared_scale_enabled: true,
    per_frame_scale_enabled: false,
    width_constraint_enabled: false
  };
}

export function createExportRequestConfig(settings: ExportConfig): Partial<ExportConfig> {
  return {
    auto_layout: settings.auto_layout,
    rows: settings.rows,
    columns: settings.columns,
    max_columns: settings.max_columns,
    cell_width: settings.cell_width,
    cell_height: settings.cell_height,
    fps: settings.fps,
    center_x: settings.center_x,
    baseline_y: settings.baseline_y,
    target_body_height: settings.target_body_height,
    height_top_y: settings.height_top_y,
    alpha_threshold: settings.alpha_threshold,
    min_pixels_per_row: settings.min_pixels_per_row,
    soft_width_limit: settings.soft_width_limit,
    shared_scale_enabled: settings.shared_scale_enabled,
    per_frame_scale_enabled: settings.per_frame_scale_enabled,
    width_constraint_enabled: settings.width_constraint_enabled
  };
}

function exportDefaults(session: SessionState | null): ExportConfig {
  return {
    ...createDefaultExportConfig(),
    ...(session?.export ?? {})
  };
}
