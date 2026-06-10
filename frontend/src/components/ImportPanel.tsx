import { Upload, Video } from "lucide-react";
import { useRef, type ChangeEvent, type ReactNode } from "react";
import type { SessionState } from "../api/types";
import { firstVideoFile, videoAccept } from "../utils/videoFiles";

type ImportPanelProps = {
  session: SessionState | null;
  sampleInterval: number;
  loading: boolean;
  error: string | null;
  onSampleIntervalChange: (interval: number) => void;
  onImportVideo: (file: File) => void;
};

export function ImportPanel({
  session,
  sampleInterval,
  loading,
  error,
  onSampleIntervalChange,
  onImportVideo
}: ImportPanelProps) {
  const videoInputRef = useRef<HTMLInputElement>(null);

  function handleVideoInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = firstVideoFile(event.currentTarget.files ?? []);
    event.currentTarget.value = "";
    if (file) {
      onImportVideo(file);
    }
  }

  return (
    <aside className="panel project-panel" aria-label="视频导入面板">
      <PanelTitle icon={<Video size={17} aria-hidden="true" />} title="自动处理流" />

      <div className="control-stack" style={{ marginTop: '20px' }}>
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
          className="primary-button full-width"
          style={{ padding: '16px', fontSize: '1.1em', display: 'flex', justifyContent: 'center', gap: '8px' }}
          onClick={() => videoInputRef.current?.click()}
          disabled={loading}
        >
          <Upload size={20} aria-hidden="true" />
          {loading ? "处理中..." : "导入视频并自动抠图"}
        </button>

        <div style={{ marginTop: '20px' }}>
          <label className="field">
            <span>抽帧间隔 (几帧抽一次)</span>
            <input
              type="number"
              min={1}
              step={1}
              value={sampleInterval}
              onChange={(event) => onSampleIntervalChange(toPositiveInteger(event.target.value))}
            />
          </label>
        </div>
        <p className="helper-text" style={{ marginTop: '16px', lineHeight: '1.5' }}>
          无需繁琐的项目设置，直接导入视频。系统将自动进行抽帧、高精度绿幕抠像以及溢色修复。<br/><br/>
          如果有极少数未扣干净的细节，可以直接在右侧进行本地精修。
        </p>
      </div>

      <div style={{ flex: 1 }} />

      <div className="status-box" aria-live="polite">
        <span className={error ? "status-error" : "status-ok"}>
          {error ?? (loading ? "正在全自动处理中，请稍候..." : session?.video_name ? `当前视频: ${session.video_name}` : "等待导入...")}
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
