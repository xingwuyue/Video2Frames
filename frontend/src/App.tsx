import {
  Layers3,
  Info
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { importVideo, getState } from "./api/client";
import type { SessionState } from "./api/types";
import { ExportPanel } from "./components/ExportPanel";
import { FrameTimeline } from "./components/FrameTimeline";
import { ImportPanel } from "./components/ImportPanel";
import { RefineEditor } from "./components/RefineEditor";
import { advancePlaybackFrame, playbackFrameIds, previousPlaybackFrame } from "./utils/playback";
import type { PreviewBackground } from "./utils/previewBackground";

export function App() {
  const [session, setSession] = useState<SessionState | null>(null);
  const [sampleInterval, setSampleInterval] = useState(3);
  const [previewBackground, setPreviewBackground] = useState<PreviewBackground>("checkerboard");
  const [selectedFrameId, setSelectedFrameId] = useState<string | null>(null);
  const [enabledFrameIds, setEnabledFrameIds] = useState<Set<string>>(() => new Set());
  const [hiddenFrameIds, setHiddenFrameIds] = useState<Set<string>>(() => new Set());
  const [deletedFrameIds, setDeletedFrameIds] = useState<Set<string>>(() => new Set());
  const [isPlaying, setIsPlaying] = useState(false);
  const [loopPlayback, setLoopPlayback] = useState(true);
  const [playbackFps, setPlaybackFps] = useState(12);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Try loading existing session state on mount
    getState()
      .then((state) => {
        if (state.video_path) {
          applySessionState(state);
        }
      })
      .catch((_) => {
        // Ignored, backend might have just restarted or no session exists.
      });
  }, []);

  const selectedFrame = useMemo(
    () => session?.frames.find((frame) => frame.id === selectedFrameId) ?? null,
    [session, selectedFrameId]
  );
  const exportEnabledFrameCount = useMemo(
    () =>
      session?.frames.filter(
        (frame) =>
          enabledFrameIds.has(frame.id) && !hiddenFrameIds.has(frame.id) && !deletedFrameIds.has(frame.id)
      ).length ?? 0,
    [deletedFrameIds, enabledFrameIds, hiddenFrameIds, session]
  );
  const playableFrameIds = useMemo(
    () => playbackFrameIds(session?.frames ?? [], enabledFrameIds, hiddenFrameIds, deletedFrameIds),
    [deletedFrameIds, enabledFrameIds, hiddenFrameIds, session]
  );
  const currentPlaybackIndex = selectedFrameId ? playableFrameIds.indexOf(selectedFrameId) : -1;

  useEffect(() => {
    if (!isPlaying) {
      return;
    }
    if (playableFrameIds.length === 0) {
      setIsPlaying(false);
      return;
    }

    const intervalMs = Math.max(50, Math.round(1000 / playbackFps));
    const timer = window.setInterval(() => {
      setSelectedFrameId((current) => {
        const next = advancePlaybackFrame(playableFrameIds, current, loopPlayback);
        if (next.shouldStop) {
          setIsPlaying(false);
        }
        return next.frameId ?? current;
      });
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [isPlaying, loopPlayback, playbackFps, playableFrameIds]);

  function applySessionState(nextSession: SessionState) {
    setSession(nextSession);
    setSampleInterval(nextSession.sample_every_n_frames);
    setIsPlaying(false);
    setEnabledFrameIds(new Set(nextSession.frames.filter((frame) => frame.enabled).map((frame) => frame.id)));
    setHiddenFrameIds(new Set());
    setDeletedFrameIds(new Set());
    setSelectedFrameId((current) => {
      if (current && nextSession.frames.some((frame) => frame.id === current)) {
        return current;
      }
      return nextSession.frames[0]?.id ?? null;
    });
  }

  async function runSessionAction(action: () => Promise<SessionState>) {
    setLoading(true);
    setError(null);
    try {
      const nextSession = await action();
      applySessionState(nextSession);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "操作失败。");
    } finally {
      setLoading(false);
    }
  }

  function handleImportVideo(file: File) {
    void runSessionAction(() => importVideo(file, sampleInterval));
  }

  function handleTogglePlayback() {
    if (playableFrameIds.length === 0) {
      setIsPlaying(false);
      return;
    }
    if (!selectedFrameId || !playableFrameIds.includes(selectedFrameId)) {
      setSelectedFrameId(playableFrameIds[0]);
    }
    setIsPlaying((current) => !current);
  }

  function handleNextPlaybackFrame() {
    const next = advancePlaybackFrame(playableFrameIds, selectedFrameId, loopPlayback);
    if (next.frameId) {
      setSelectedFrameId(next.frameId);
    }
  }

  function handlePreviousPlaybackFrame() {
    const previous = previousPlaybackFrame(playableFrameIds, selectedFrameId, loopPlayback);
    if (previous) {
      setSelectedFrameId(previous);
    }
  }

  function handlePlaybackFpsChange(fps: number) {
    setPlaybackFps(Math.min(60, Math.max(1, Math.floor(fps || 1))));
  }

  function toggleFrameEnabled(frameId: string) {
    setEnabledFrameIds((current) => {
      const next = new Set(current);
      if (next.has(frameId)) {
        next.delete(frameId);
      } else {
        next.add(frameId);
      }
      return next;
    });
  }

  function hideFrame(frameId: string) {
    setHiddenFrameIds((current) => new Set(current).add(frameId));
    selectNextVisibleFrame(frameId, new Set(hiddenFrameIds).add(frameId), deletedFrameIds);
  }

  function deleteFrame(frameId: string) {
    setDeletedFrameIds((current) => new Set(current).add(frameId));
    selectNextVisibleFrame(frameId, hiddenFrameIds, new Set(deletedFrameIds).add(frameId));
  }

  function selectNextVisibleFrame(frameId: string, nextHidden: Set<string>, nextDeleted: Set<string>) {
    if (selectedFrameId !== frameId) {
      return;
    }
    const nextFrame = session?.frames.find(
      (frame) => frame.id !== frameId && !nextHidden.has(frame.id) && !nextDeleted.has(frame.id)
    );
    setSelectedFrameId(nextFrame?.id ?? null);
  }

  return (
    <main className="workbench">
      <header className="topbar">
        <div className="brand">
          <Layers3 size={20} aria-hidden="true" />
          <span>SpriteSheet 工具</span>
        </div>
      </header>

      <section className="workspace" aria-label="SpriteSheet 工作台">
        <ImportPanel
          session={session}
          sampleInterval={sampleInterval}
          loading={loading}
          error={error}
          onSampleIntervalChange={setSampleInterval}
          onImportVideo={handleImportVideo}
        />

        <section className="editor-column" aria-label="预览和时间轴">
          <RefineEditor
            frame={selectedFrame}
            previewBackground={previewBackground}
            onPreviewBackgroundChange={setPreviewBackground}
            onImportVideo={handleImportVideo}
            playback={{
              canPlay: playableFrameIds.length > 0,
              currentFrameNumber: currentPlaybackIndex >= 0 ? currentPlaybackIndex + 1 : 0,
              frameCount: playableFrameIds.length,
              fps: playbackFps,
              isPlaying,
              loop: loopPlayback,
              onFpsChange: handlePlaybackFpsChange,
              onNextFrame: handleNextPlaybackFrame,
              onPreviousFrame: handlePreviousPlaybackFrame,
              onToggleLoop: () => setLoopPlayback((current) => !current),
              onTogglePlay: handleTogglePlayback
            }}
          />

          <FrameTimeline
            frames={session?.frames ?? []}
            selectedFrameId={selectedFrameId}
            enabledFrameIds={enabledFrameIds}
            hiddenFrameIds={hiddenFrameIds}
            deletedFrameIds={deletedFrameIds}
            onSelectFrame={setSelectedFrameId}
            onToggleEnabled={toggleFrameEnabled}
            onHideFrame={hideFrame}
            onDeleteFrame={deleteFrame}
          />
        </section>

        <aside className="panel status-panel" aria-label="状态和导出面板">
          <PanelTitle icon={<Info size={17} aria-hidden="true" />} title="状态" />
          <div className="settings-stack">
            <div className="setting-row">
              <span>视频</span>
              <strong>{session?.video_name ?? "未导入"}</strong>
            </div>
            <div className="setting-row">
              <span>帧数</span>
              <strong>{session?.frames.length ?? 0}</strong>
            </div>
            <div className="setting-row">
              <span>本地启用</span>
              <strong>{exportEnabledFrameCount}</strong>
            </div>
            <div className="setting-row">
              <span>本地隐藏/删除</span>
              <strong>{hiddenFrameIds.size + deletedFrameIds.size}</strong>
            </div>
          </div>
          <p className="helper-text">时间轴调整目前只影响本地预览，不会写回后端。</p>
          <div className="panel-divider" />
          <ExportPanel session={session} enabledFrameCount={exportEnabledFrameCount} />
        </aside>
      </section>
    </main>
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
