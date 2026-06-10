import {
  Check,
  Eraser,
  Hand,
  Maximize,
  Paintbrush,
  Pipette,
  Pause,
  Play,
  Repeat,
  SkipBack,
  SkipForward,
  Undo2,
  WandSparkles,
  X,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import { fileUrl } from "../api/client";
import type { FrameRecord } from "../api/types";
import { fitToViewport } from "../utils/canvasTools";
import { connectedColorMask, globalColorMask } from "../utils/floodFill";
import { previewBackgroundModes, type PreviewBackground } from "../utils/previewBackground";
import { keyedPreviewPath, shouldCancelSmartPreview, type RefineToolMode } from "../utils/refinePreview";
import { firstVideoFile } from "../utils/videoFiles";

type ToolMode = RefineToolMode;
type Point = { x: number; y: number };

type RefineEditorProps = {
  frame: FrameRecord | null;
  previewBackground: PreviewBackground;
  onPreviewBackgroundChange: (background: PreviewBackground) => void;
  onImportVideo: (file: File) => void;
  playback: {
    canPlay: boolean;
    currentFrameNumber: number;
    frameCount: number;
    fps: number;
    isPlaying: boolean;
    loop: boolean;
    onFpsChange: (fps: number) => void;
    onNextFrame: () => void;
    onPreviousFrame: () => void;
    onToggleLoop: () => void;
    onTogglePlay: () => void;
  };
};

const minZoom = 0.1;
const maxZoom = 12;

export function RefineEditor({
  frame,
  previewBackground,
  onPreviewBackgroundChange,
  onImportVideo,
  playback
}: RefineEditorProps) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement | null>(null);
  const undoStackRef = useRef<ImageData[]>([]);
  const smartMaskRef = useRef<Uint8Array | null>(null);
  const smartPreviewMetaRef = useRef<{ mode: ToolMode; imageKey: string | null; tolerance: number } | null>(null);
  const drawingRef = useRef(false);
  const panningRef = useRef(false);
  const panStartRef = useRef<Point>({ x: 0, y: 0 });
  const activePointerRef = useRef<number | null>(null);

  const [mode, setMode] = useState<ToolMode>("erase");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  const [brushSize, setBrushSize] = useState(18);
  const [hardness, setHardness] = useState(70);
  const [tolerance, setTolerance] = useState(36);
  const [spaceHeld, setSpaceHeld] = useState(false);
  const [hasImage, setHasImage] = useState(false);
  const [hasPreview, setHasPreview] = useState(false);
  const [brushCursor, setBrushCursor] = useState<Point | null>(null);
  const [status, setStatus] = useState("选择一帧开始本地精修。");

  const imagePath = keyedPreviewPath(frame);
  const imageUrl = imagePath ? fileUrl(imagePath) : null;
  const frameNeedsKeying = Boolean(frame && !frame.keyed_path);
  const cursor = spaceHeld ? "grab" : mode === "color" || mode === "global_color" ? "crosshair" : "none";

  const cloneCurrentImage = useCallback(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return null;
    }
    return context.getImageData(0, 0, canvas.width, canvas.height);
  }, []);

  const pushUndo = useCallback(() => {
    const snapshot = cloneCurrentImage();
    if (!snapshot) {
      return;
    }
    undoStackRef.current = [...undoStackRef.current.slice(-9), snapshot];
  }, [cloneCurrentImage]);

  const redrawOverlay = useCallback(() => {
    const canvas = canvasRef.current;
    const overlay = overlayRef.current;
    const mask = smartMaskRef.current;
    const context = overlay?.getContext("2d");
    if (!canvas || !overlay || !context) {
      return;
    }

    overlay.width = canvas.width;
    overlay.height = canvas.height;
    context.clearRect(0, 0, overlay.width, overlay.height);
    if (!mask) {
      setHasPreview(false);
      return;
    }

    const preview = context.createImageData(canvas.width, canvas.height);
    for (let index = 0; index < mask.length; index += 1) {
      if (!mask[index]) {
        continue;
      }
      const dataIndex = index * 4;
      preview.data[dataIndex] = 255;
      preview.data[dataIndex + 1] = 82;
      preview.data[dataIndex + 2] = 82;
      preview.data[dataIndex + 3] = 132;
    }
    context.putImageData(preview, 0, 0);
    setHasPreview(true);
  }, []);

  const fitCanvasToViewport = useCallback(() => {
    const viewport = viewportRef.current;
    const canvas = canvasRef.current;
    if (!viewport || !canvas || canvas.width === 0 || canvas.height === 0) {
      return;
    }
    const availableWidth = Math.max(1, viewport.clientWidth - 32);
    const availableHeight = Math.max(1, viewport.clientHeight - 32);
    const nextZoom = fitToViewport(canvas.width, canvas.height, availableWidth, availableHeight);
    setZoom(Math.min(maxZoom, Math.max(minZoom, nextZoom)));
    setPan({ x: 0, y: 0 });
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.code === "Space") {
        setSpaceHeld(true);
      }
    };
    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.code === "Space") {
        setSpaceHeld(false);
        panningRef.current = false;
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const overlay = overlayRef.current;
    const context = canvas?.getContext("2d");
    const overlayContext = overlay?.getContext("2d");
    undoStackRef.current = [];
    smartMaskRef.current = null;
    smartPreviewMetaRef.current = null;
    setHasPreview(false);

    if (!canvas || !overlay || !context || !overlayContext || !imagePath || !imageUrl) {
      setHasImage(false);
      setStatus(frameNeedsKeying ? "当前帧还没有自动抠图结果，请重新加载项目或执行抠图。" : "选择一帧开始本地精修。");
      return;
    }

    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => {
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      overlay.width = image.naturalWidth;
      overlay.height = image.naturalHeight;
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0);
      overlayContext.clearRect(0, 0, overlay.width, overlay.height);
      setHasImage(true);
      setStatus("本地预览和编辑状态，改动暂不写回后端。");
      window.requestAnimationFrame(fitCanvasToViewport);
    };
    image.onerror = () => {
      canvas.width = 352;
      canvas.height = 352;
      overlay.width = 352;
      overlay.height = 352;
      drawFallbackFrame(context, imagePath);
      overlayContext.clearRect(0, 0, overlay.width, overlay.height);
      setHasImage(true);
      setStatus("浏览器无法加载该图片路径，当前显示本地占位预览。");
      window.requestAnimationFrame(fitCanvasToViewport);
    };
    image.src = imageUrl;
  }, [fitCanvasToViewport, frameNeedsKeying, imagePath, imageUrl]);

  useEffect(() => {
    const previous = smartPreviewMetaRef.current;
    if (
      !previous ||
      !shouldCancelSmartPreview({
        hasPreview,
        previousMode: previous.mode,
        nextMode: mode,
        previousImageKey: previous.imageKey,
        nextImageKey: imagePath,
        previousTolerance: previous.tolerance,
        nextTolerance: tolerance
      })
    ) {
      return;
    }

    cancelSmartPreview();
    setStatus("工具状态已变化，同色擦除预览已取消。");
  }, [hasPreview, imagePath, mode, tolerance]);

  function updateZoom(nextZoom: number) {
    setZoom(Math.min(maxZoom, Math.max(minZoom, nextZoom)));
  }

  function pointFromEvent(event: React.PointerEvent<HTMLDivElement>): Point | null {
    const canvas = canvasRef.current;
    if (!canvas) {
      return null;
    }
    const bounds = canvas.getBoundingClientRect();
    if (bounds.width === 0 || bounds.height === 0) {
      return null;
    }
    return {
      x: Math.floor(((event.clientX - bounds.left) / bounds.width) * canvas.width),
      y: Math.floor(((event.clientY - bounds.top) / bounds.height) * canvas.height)
    };
  }

  function applyBrush(point: Point) {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context || point.x < 0 || point.y < 0 || point.x >= canvas.width || point.y >= canvas.height) {
      return;
    }

    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    const radius = Math.max(1, brushSize / 2);
    const hardRadius = radius * (hardness / 100);
    const left = Math.max(0, Math.floor(point.x - radius));
    const right = Math.min(canvas.width - 1, Math.ceil(point.x + radius));
    const top = Math.max(0, Math.floor(point.y - radius));
    const bottom = Math.min(canvas.height - 1, Math.ceil(point.y + radius));

    for (let y = top; y <= bottom; y += 1) {
      for (let x = left; x <= right; x += 1) {
        const distance = Math.hypot(x - point.x, y - point.y);
        if (distance > radius) {
          continue;
        }
        const edgeSpan = Math.max(1, radius - hardRadius);
        const strength = distance <= hardRadius ? 1 : Math.max(0, 1 - (distance - hardRadius) / edgeSpan);
        const alphaIndex = (y * canvas.width + x) * 4 + 3;
        if (mode === "erase") {
          imageData.data[alphaIndex] = Math.round(imageData.data[alphaIndex] * (1 - strength));
        } else {
          imageData.data[alphaIndex] = Math.round(imageData.data[alphaIndex] + (255 - imageData.data[alphaIndex]) * strength);
        }
      }
    }

    context.putImageData(imageData, 0, 0);
  }

  function createSmartPreview(point: Point) {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context || point.x < 0 || point.y < 0 || point.x >= canvas.width || point.y >= canvas.height) {
      return;
    }

    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    const mask = mode === "global_color"
      ? globalColorMask(imageData.data, canvas.width, canvas.height, point.x, point.y, tolerance)
      : connectedColorMask(imageData.data, canvas.width, canvas.height, point.x, point.y, tolerance);
    smartMaskRef.current = mask;
    smartPreviewMetaRef.current = { mode, imageKey: imagePath, tolerance };
    redrawOverlay();
    setStatus("同色擦除预览已生成，请先应用或取消后再选择其他区域。");
  }

  function applySmartErase() {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    const mask = smartMaskRef.current;
    if (!canvas || !context || !mask) {
      return;
    }
    pushUndo();
    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    for (let index = 0; index < mask.length; index += 1) {
      if (mask[index]) {
        imageData.data[index * 4 + 3] = 0;
      }
    }
    context.putImageData(imageData, 0, 0);
    cancelSmartPreview();
    setStatus("同色擦除已应用到本地画布，可使用撤销恢复。");
  }

  function cancelSmartPreview() {
    smartMaskRef.current = null;
    smartPreviewMetaRef.current = null;
    redrawOverlay();
  }

  function undo() {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    const previous = undoStackRef.current.pop();
    if (!canvas || !context || !previous) {
      return;
    }
    context.putImageData(previous, 0, 0);
    cancelSmartPreview();
    setStatus("已撤销到上一个本地画布状态。");
  }

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>) {
    if (!hasImage) {
      return;
    }
    activePointerRef.current = event.pointerId;
    event.currentTarget.setPointerCapture(event.pointerId);
    if (event.button === 1 || spaceHeld) {
      panningRef.current = true;
      panStartRef.current = { x: event.clientX - pan.x, y: event.clientY - pan.y };
      return;
    }
    if (mode === "color" || mode === "global_color") {
      const point = pointFromEvent(event);
      if (point) {
        createSmartPreview(point);
      }
      return;
    }

    cancelSmartPreview();
    pushUndo();
    drawingRef.current = true;
    const point = pointFromEvent(event);
    if (point) {
      applyBrush(point);
    }
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (panningRef.current) {
      setBrushCursor(null);
      setPan({ x: event.clientX - panStartRef.current.x, y: event.clientY - panStartRef.current.y });
      return;
    }
    const point = pointFromEvent(event);
    setBrushCursor(point);
    if (!drawingRef.current || activePointerRef.current !== event.pointerId) {
      return;
    }
    if (point) {
      applyBrush(point);
    }
  }

  function endPointer(event: React.PointerEvent<HTMLDivElement>) {
    drawingRef.current = false;
    panningRef.current = false;
    if (activePointerRef.current === event.pointerId) {
      activePointerRef.current = null;
    }
  }

  function handleWheel(event: React.WheelEvent<HTMLDivElement>) {
    if (!hasImage) {
      return;
    }
    event.preventDefault();
    updateZoom(zoom * (event.deltaY < 0 ? 1.12 : 0.89));
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const file = firstVideoFile(event.dataTransfer.files);
    if (file) {
      onImportVideo(file);
    }
  }

  return (
    <section className="refine-editor" aria-label="预览和精修编辑器">
      <div className="refine-toolbar">
        <div className="refine-toolbar-left">
          <div className="panel-title">
            <WandSparkles size={17} aria-hidden="true" />
            <h2>预览 / 精修</h2>
          </div>
          <div className="segmented-control" aria-label="预览背景">
            {previewBackgroundModes.map((background) => (
              <button
                type="button"
                key={background.value}
                className={background.value === previewBackground ? "active" : ""}
                aria-pressed={background.value === previewBackground}
                onClick={() => onPreviewBackgroundChange(background.value)}
              >
                {background.label}
              </button>
            ))}
          </div>
        </div>
        <div className="toolbar-group" aria-label="视图控制">
          <div className="playback-controls" aria-label="序列播放控制">
            <button className="icon-button" type="button" title="上一帧" disabled={!playback.canPlay} onClick={playback.onPreviousFrame}>
              <SkipBack size={16} aria-hidden="true" />
            </button>
            <button className="icon-button" type="button" title={playback.isPlaying ? "暂停" : "播放"} disabled={!playback.canPlay} onClick={playback.onTogglePlay}>
              {playback.isPlaying ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
            </button>
            <button className="icon-button" type="button" title="下一帧" disabled={!playback.canPlay} onClick={playback.onNextFrame}>
              <SkipForward size={16} aria-hidden="true" />
            </button>
            <span className="frame-readout">
              {playback.currentFrameNumber}/{playback.frameCount}
            </span>
            <button
              className={playback.loop ? "tool-button labeled active" : "tool-button labeled"}
              type="button"
              title="循环播放"
              aria-pressed={playback.loop}
              onClick={playback.onToggleLoop}
            >
              <Repeat size={15} aria-hidden="true" />
              循环
            </button>
            <label className="fps-control">
              <span>FPS</span>
              <input
                type="number"
                min={1}
                max={60}
                value={playback.fps}
                onChange={(event) => playback.onFpsChange(Number(event.target.value))}
              />
            </label>
          </div>
          <button className="icon-button" type="button" title="缩小" onClick={() => updateZoom(zoom / 1.2)}>
            <ZoomOut size={16} aria-hidden="true" />
          </button>
          <span className="zoom-readout">{Math.round(zoom * 100)}%</span>
          <button className="icon-button" type="button" title="放大" onClick={() => updateZoom(zoom * 1.2)}>
            <ZoomIn size={16} aria-hidden="true" />
          </button>
          <button className="tool-button labeled" type="button" title="适配窗口" onClick={fitCanvasToViewport}>
            <Maximize size={16} aria-hidden="true" />
            适配
          </button>
          <button className="tool-button labeled" type="button" title="100% 视图" onClick={() => updateZoom(1)}>
            100%
          </button>
          <button className="icon-button" type="button" title="撤销本地编辑" onClick={undo}>
            <Undo2 size={16} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="refine-body">
        <aside className="refine-tools" aria-label="精修工具">
          <div className="tool-mode-grid" role="group" aria-label="笔刷模式">
            <button type="button" className={mode === "erase" ? "active" : ""} onClick={() => setMode("erase")}>
              <Eraser size={15} aria-hidden="true" />
              擦除
            </button>
            <button type="button" className={mode === "restore" ? "active" : ""} onClick={() => setMode("restore")}>
              <Paintbrush size={15} aria-hidden="true" />
              恢复
            </button>
            <button type="button" className={mode === "color" ? "active" : ""} onClick={() => setMode("color")}>
              <Pipette size={15} aria-hidden="true" />
              同色擦除
            </button>
            <button type="button" className={mode === "global_color" ? "active" : ""} onClick={() => setMode("global_color")}>
              <Pipette size={15} aria-hidden="true" />
              全局同色擦除
            </button>
          </div>

          <label className="field compact-field">
            大小
            <input type="range" min="2" max="96" value={brushSize} onChange={(event) => setBrushSize(Number(event.target.value))} />
            <span>{brushSize}px</span>
          </label>
          <label className="field compact-field">
            硬度
            <input type="range" min="0" max="100" value={hardness} onChange={(event) => setHardness(Number(event.target.value))} />
            <span>{hardness}%</span>
          </label>
          <label className="field compact-field">
            容差
            <input type="range" min="0" max="160" value={tolerance} onChange={(event) => setTolerance(Number(event.target.value))} />
            <span>{tolerance}</span>
          </label>

          <div className="smart-actions">
            <button className="primary-button" type="button" disabled={!hasPreview} onClick={applySmartErase}>
              <Check size={15} aria-hidden="true" />
              应用
            </button>
            <button className="secondary-button" type="button" disabled={!hasPreview} onClick={cancelSmartPreview}>
              <X size={15} aria-hidden="true" />
              取消
            </button>
          </div>
          <p className="helper-text">
            同色擦除会选中与点击点相连且颜色接近的区域；全局同色擦除会选中整张图颜色接近的区域。当前只编辑本地预览，暂不改变后端文件。
          </p>
        </aside>

        <div
          className={`refine-viewport refine-bg-${previewBackground} ${zoom >= 6 ? "show-grid" : ""}`}
          ref={viewportRef}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={endPointer}
          onPointerCancel={endPointer}
          onWheel={handleWheel}
          style={{ cursor }}
        >
          <div className="canvas-transform" style={{ transform: `translate(-50%, -50%) translate(${pan.x}px, ${pan.y}px)` }}>
            <canvas
              ref={canvasRef}
              className="refine-canvas"
              style={{ width: `${(canvasRef.current?.width ?? 352) * zoom}px` }}
            />
            <canvas
              ref={overlayRef}
              className="refine-overlay"
              style={{ width: `${(canvasRef.current?.width ?? 352) * zoom}px` }}
            />
            {hasImage && mode !== "color" && mode !== "global_color" ? (
              <div
                className="brush-cursor"
                aria-hidden="true"
                style={{
                  width: `${brushSize * zoom}px`,
                  height: `${brushSize * zoom}px`,
                  opacity: brushCursor ? 1 : 0,
                  transform: brushCursor
                    ? `translate(${brushCursor.x * zoom - (brushSize * zoom) / 2}px, ${
                        brushCursor.y * zoom - (brushSize * zoom) / 2
                      }px)`
                    : undefined
                }}
              />
            ) : null}
          </div>
          {!hasImage ? (
            <div className="refine-empty">
              <Hand size={28} aria-hidden="true" />
              <span>
                {frameNeedsKeying
                  ? "当前帧还没有抠图结果，请重新加载项目或执行抠图。"
                  : "选择一帧进行本地编辑，或拖入视频重新导入。"}
              </span>
            </div>
          ) : null}
        </div>
      </div>
      <div className="refine-status">{status}</div>
    </section>
  );
}

function drawFallbackFrame(context: CanvasRenderingContext2D, label: string) {
  const size = 352;
  context.clearRect(0, 0, size, size);
  context.fillStyle = "rgba(255, 255, 255, 0)";
  context.fillRect(0, 0, size, size);
  context.fillStyle = "rgba(51, 61, 72, 0.92)";
  context.fillRect(116, 84, 120, 200);
  context.fillStyle = "rgba(87, 154, 166, 0.95)";
  context.fillRect(92, 76, 72, 82);
  context.fillStyle = "#f1f4f7";
  context.font = "12px sans-serif";
  context.textAlign = "center";
  context.fillText("本地预览", 176, 304);
  context.fillStyle = "#aab3c0";
  context.font = "10px sans-serif";
  context.fillText(label.split(/[\\/]/).pop()?.slice(0, 28) ?? "frame", 176, 326);
}
