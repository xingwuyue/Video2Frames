export type RefineToolMode = "erase" | "restore" | "color" | "global_color";

type SmartPreviewLifecycle = {
  hasPreview: boolean;
  previousMode: RefineToolMode;
  nextMode: RefineToolMode;
  previousImageKey: string | null;
  nextImageKey: string | null;
  previousTolerance: number;
  nextTolerance: number;
};

export function shouldCancelSmartPreview({
  hasPreview,
  previousMode,
  nextMode,
  previousImageKey,
  nextImageKey,
  previousTolerance,
  nextTolerance
}: SmartPreviewLifecycle): boolean {
  if (!hasPreview) {
    return false;
  }

  return previousMode !== nextMode || (nextMode !== "color" && nextMode !== "global_color") || previousImageKey !== nextImageKey || previousTolerance !== nextTolerance;
}

export function keyedPreviewPath(frame: { keyed_path: string | null } | null): string | null {
  return frame?.keyed_path ?? null;
}
