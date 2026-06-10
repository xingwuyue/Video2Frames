import { FilePlus2, FolderOpen, Loader2, SlidersHorizontal, Upload, Wand2 } from "lucide-react";
import { useRef, type ChangeEvent, type ReactNode } from "react";
import type { BackgroundKey, BackgroundKeyMode, ProjectConfig } from "../api/types";
import { firstVideoFile, videoAccept } from "../utils/videoFiles";

type ProjectPanelProps = {
  project: ProjectConfig | null;
  projectName: string;
  sampleInterval: number;
  background: BackgroundKey;
  loading: boolean;
  error: string | null;
  onProjectNameChange: (name: string) => void;
  onSampleIntervalChange: (interval: number) => void;
  onBackgroundChange: (background: BackgroundKey) => void;
  onCreateProject: () => void;
  onLoadProject: () => void;
  onImportVideo: (file: File) => void;
  onProcessKey: () => void;
};

const backgroundModes: Array<{ value: BackgroundKeyMode; label: string }> = [
  { value: "green", label: "绿色" },
  { value: "red_purple", label: "红紫色" },
  { value: "blue", label: "蓝色" },
  { value: "white", label: "白色" },
  { value: "custom", label: "自定义" }
];

export function ProjectPanel({
  project,
  projectName,
  sampleInterval,
  background,
  loading,
  error,
  onProjectNameChange,
  onSampleIntervalChange,
  onBackgroundChange,
  onCreateProject,
  onLoadProject,
  onImportVideo,
  onProcessKey
}: ProjectPanelProps) {
  const videoInputRef = useRef<HTMLInputElement>(null);

  function handleVideoInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = firstVideoFile(event.currentTarget.files ?? []);
    event.currentTarget.value = "";
    if (file) {
      onImportVideo(file);
    }
  }

  return (
    <aside className="panel project-panel" aria-label="项目面板">
      <PanelTitle icon={<FolderOpen size={17} aria-hidden="true" />} title="项目" />

      <div className="control-stack">
        <label className="field">
          <span>项目名称</span>
          <input
            value={projectName}
            onChange={(event) => onProjectNameChange(event.target.value)}
            placeholder="walk-cycle"
            disabled={loading}
          />
        </label>

        <div className="button-row">
          <button type="button" className="primary-button" onClick={onCreateProject} disabled={loading}>
            <FilePlus2 size={16} aria-hidden="true" />
            创建
          </button>
          <button type="button" className="secondary-button" onClick={onLoadProject} disabled={loading}>
            <FolderOpen size={16} aria-hidden="true" />
            加载
          </button>
        </div>

        <input
          ref={videoInputRef}
          type="file"
          accept={videoAccept}
          className="hidden-file-input"
          aria-label="选择要导入的视频"
          onChange={handleVideoInputChange}
        />
        <button
          type="button"
          className="secondary-button full-width"
          onClick={() => videoInputRef.current?.click()}
          disabled={loading || !project}
        >
          <Upload size={16} aria-hidden="true" />
          导入视频
        </button>

        <label className="field">
          <span>抽帧间隔</span>
          <input
            type="number"
            min={1}
            step={1}
            value={sampleInterval}
            onChange={(event) => onSampleIntervalChange(toPositiveInteger(event.target.value))}
          />
        </label>
        <p className="helper-text">先创建或加载项目，再从桌面选择视频；也可以把视频拖到预览区。</p>
      </div>

      <div className="panel-divider" />

      <PanelTitle icon={<SlidersHorizontal size={17} aria-hidden="true" />} title="背景抠图" />
      <div className="control-stack compact">
        <label className="field">
          <span>模式</span>
          <select
            value={background.mode}
            onChange={(event) =>
              onBackgroundChange({ ...background, mode: event.target.value as BackgroundKeyMode })
            }
          >
            {backgroundModes.map((mode) => (
              <option key={mode.value} value={mode.value}>
                {mode.label}
              </option>
            ))}
          </select>
        </label>

        <div className="rgb-grid" aria-label="RGB 抠图颜色">
          {(["R", "G", "B"] as const).map((channel, index) => (
            <label className="field" key={channel}>
              <span>{channel}</span>
              <input
                type="number"
                min={0}
                max={255}
                value={background.color[index]}
                onChange={(event) => {
                  const nextColor: [number, number, number] = [...background.color];
                  nextColor[index] = clampColor(event.target.value);
                  onBackgroundChange({ ...background, color: nextColor });
                }}
              />
            </label>
          ))}
        </div>

        <label className="field">
          <span>容差</span>
          <input
            type="number"
            min={0}
            max={441}
            value={background.tolerance}
            onChange={(event) =>
              onBackgroundChange({
                ...background,
                tolerance: toBoundedInteger(event.target.value, 0, 441)
              })
            }
          />
        </label>

        <button
          type="button"
          className="primary-button full-width"
          onClick={onProcessKey}
          disabled={loading || !project}
        >
          {loading ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <Wand2 size={16} aria-hidden="true" />}
          执行抠图
        </button>
        <p className="helper-text">抠图参数会用于后端处理；建议绿幕使用 #00FF00。</p>
      </div>

      <div className="status-box" aria-live="polite">
        <span className={error ? "status-error" : "status-ok"}>
          {error ?? (loading ? "处理中..." : project ? `已加载 ${project.name}` : "尚未加载项目")}
        </span>
      </div>
    </aside>
  );
}

function PanelTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="panel-title">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

function toPositiveInteger(value: string): number {
  return Math.max(1, Math.floor(Number(value) || 1));
}

function toBoundedInteger(value: string, min: number, max: number): number {
  const next = Math.floor(Number(value) || min);
  return Math.min(max, Math.max(min, next));
}

function clampColor(value: string): number {
  return toBoundedInteger(value, 0, 255);
}
