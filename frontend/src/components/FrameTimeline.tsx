import { EyeOff, Layers3, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import type { FrameRecord } from "../api/types";

type FrameTimelineProps = {
  frames: FrameRecord[];
  selectedFrameId: string | null;
  enabledFrameIds: Set<string>;
  hiddenFrameIds: Set<string>;
  deletedFrameIds: Set<string>;
  onSelectFrame: (frameId: string) => void;
  onToggleEnabled: (frameId: string) => void;
  onHideFrame: (frameId: string) => void;
  onDeleteFrame: (frameId: string) => void;
};

export function FrameTimeline({
  frames,
  selectedFrameId,
  enabledFrameIds,
  hiddenFrameIds,
  deletedFrameIds,
  onSelectFrame,
  onToggleEnabled,
  onHideFrame,
  onDeleteFrame
}: FrameTimelineProps) {
  const visibleFrames = frames.filter(
    (frame) => !hiddenFrameIds.has(frame.id) && !deletedFrameIds.has(frame.id)
  );

  return (
    <section className="timeline" aria-label="帧时间轴">
      <div className="timeline-header">
        <PanelTitle icon={<Layers3 size={17} aria-hidden="true" />} title="时间轴" />
        <span className="timeline-note">启用、隐藏和删除只影响本地预览，暂不保存</span>
      </div>

      {visibleFrames.length > 0 ? (
        <div className="timeline-track" role="list">
          {visibleFrames.map((frame, index) => {
            const selected = frame.id === selectedFrameId;
            const enabled = enabledFrameIds.has(frame.id);
            return (
              <article
                className={`frame-card${selected ? " selected" : ""}${enabled ? "" : " disabled"}`}
                key={frame.id}
                role="listitem"
                aria-current={selected ? "true" : undefined}
              >
                <button type="button" className="frame-select" onClick={() => onSelectFrame(frame.id)}>
                  <span className="frame-index">{String(index + 1).padStart(2, "0")}</span>
                  <span className="frame-source">源帧 {frame.source_frame}</span>
                  <span className="frame-path">{frame.keyed_path ? "已抠图" : "原始"}</span>
                </button>
                <div className="frame-actions">
                  <label className="toggle-control">
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={() => onToggleEnabled(frame.id)}
                    />
                    <span>本地启用</span>
                  </label>
                  <div className="frame-action-buttons">
                    <button
                      type="button"
                      className="mini-icon-button"
                      onClick={() => onHideFrame(frame.id)}
                      aria-label="本地隐藏帧"
                      title="本地隐藏"
                    >
                      <EyeOff size={14} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      className="mini-icon-button danger"
                      onClick={() => onDeleteFrame(frame.id)}
                      aria-label="本地删除帧"
                      title="本地删除"
                    >
                      <Trash2 size={14} aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="empty-timeline">还没有抽取帧。</div>
      )}
    </section>
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
