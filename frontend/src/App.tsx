import {
  Layers3,
  Info
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createProject, importVideo, loadProject, processKey } from "./api/client";
import type { BackgroundKey, ProjectConfig } from "./api/types";
import { ExportPanel } from "./components/ExportPanel";
import { FrameTimeline } from "./components/FrameTimeline";
import { ProjectPanel } from "./components/ProjectPanel";
import { RefineEditor } from "./components/RefineEditor";
import { advancePlaybackFrame, playbackFrameIds, previousPlaybackFrame } from "./utils/playback";
import type { PreviewBackground } from "./utils/previewBackground";

const defaultBackground: BackgroundKey = {
  mode: "green",
  color: [0, 255, 0],
  tolerance: 45,
  edge_feather: 1,
  spill_suppression: 0.25
};

export function App() {
  const [project, setProject] = useState<ProjectConfig | null>(null);
  const [projectName, setProjectName] = useState("");
  const [sampleInterval, setSampleInterval] = useState(3);
  const [background, setBackground] = useState<BackgroundKey>(defaultBackground);
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

  const selectedFrame = useMemo(
    () => project?.frames.find((frame) => frame.id === selectedFrameId) ?? null,
    [project, selectedFrameId]
  );
  const exportEnabledFrameCount = useMemo(
    () =>
      project?.frames.filter(
        (frame) =>
          enabledFrameIds.has(frame.id) && !hiddenFrameIds.has(frame.id) && !deletedFrameIds.has(frame.id)
      ).length ?? 0,
    [deletedFrameIds, enabledFrameIds, hiddenFrameIds, project]
  );
  const playableFrameIds = useMemo(
    () => playbackFrameIds(project?.frames ?? [], enabledFrameIds, hiddenFrameIds, deletedFrameIds),
    [deletedFrameIds, enabledFrameIds, hiddenFrameIds, project]
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

  async function runProjectAction(action: () => Promise<ProjectConfig>) {
    setLoading(true);
    setError(null);
    try {
      const nextProject = await action();
      setProject(nextProject);
      setProjectName(nextProject.name);
      setSampleInterval(nextProject.sample_every_n_frames);
      setBackground(nextProject.background);
      setIsPlaying(false);
      setEnabledFrameIds(new Set(nextProject.frames.filter((frame) => frame.enabled).map((frame) => frame.id)));
      setHiddenFrameIds(new Set());
      setDeletedFrameIds(new Set());
      setSelectedFrameId((current) => {
        if (current && nextProject.frames.some((frame) => frame.id === current)) {
          return current;
        }
        return nextProject.frames[0]?.id ?? null;
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "项目操作失败。");
    } finally {
      setLoading(false);
    }
  }

  function handleCreateProject() {
    const name = projectName.trim();
    if (!name) {
      setError("请先输入项目名称。");
      return;
    }
    void runProjectAction(() => createProject(name));
  }

  function handleLoadProject() {
    const name = projectName.trim();
    if (!name) {
      setError("请先输入项目名称。");
      return;
    }
    void runProjectAction(() => loadProject(name));
  }

  function handleProcessKey() {
    if (!project) {
      setError("请先加载或创建项目。");
      return;
    }
    void runProjectAction(() => processKey(project.name));
  }

  function handleImportVideo(file: File) {
    if (!project) {
      setError("请先创建或加载项目。");
      return;
    }
    void runProjectAction(() => importVideo(project.name, file, sampleInterval));
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
    const nextFrame = project?.frames.find(
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
        <ProjectPanel
          project={project}
          projectName={projectName}
          sampleInterval={sampleInterval}
          background={background}
          loading={loading}
          error={error}
          onProjectNameChange={setProjectName}
          onSampleIntervalChange={setSampleInterval}
          onBackgroundChange={setBackground}
          onCreateProject={handleCreateProject}
          onLoadProject={handleLoadProject}
          onImportVideo={handleImportVideo}
          onProcessKey={handleProcessKey}
        />

        <section className="editor-column" aria-label="预览和时间轴">
          <RefineEditor
            frame={selectedFrame}
            projectName={project?.name ?? null}
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
            frames={project?.frames ?? []}
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

        <aside className="panel status-panel" aria-label="项目状态和导出面板">
          <PanelTitle icon={<Info size={17} aria-hidden="true" />} title="状态" />
          <div className="settings-stack">
            <div className="setting-row">
              <span>项目</span>
              <strong>{project?.name ?? "未加载"}</strong>
            </div>
            <div className="setting-row">
              <span>帧数</span>
              <strong>{project?.frames.length ?? 0}</strong>
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
          <ExportPanel project={project} enabledFrameCount={exportEnabledFrameCount} />
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
