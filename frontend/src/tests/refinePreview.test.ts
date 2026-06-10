import { describe, expect, it } from "vitest";
import { keyedPreviewPath, shouldCancelSmartPreview } from "../utils/refinePreview";

describe("shouldCancelSmartPreview", () => {
  it("keeps a color erase preview only when color mode, image key, and tolerance are unchanged", () => {
    expect(
      shouldCancelSmartPreview({
        hasPreview: true,
        previousMode: "color",
        nextMode: "color",
        previousImageKey: "frame-1.png",
        nextImageKey: "frame-1.png",
        previousTolerance: 36,
        nextTolerance: 36
      })
    ).toBe(false);
  });

  it("cancels a smart preview when mode, image key, or tolerance changes", () => {
    const current = {
      hasPreview: true,
      previousMode: "color",
      previousImageKey: "frame-1.png",
      previousTolerance: 36
    } as const;

    expect(shouldCancelSmartPreview({ ...current, nextMode: "erase", nextImageKey: "frame-1.png", nextTolerance: 36 })).toBe(true);
    expect(shouldCancelSmartPreview({ ...current, nextMode: "color", nextImageKey: "frame-2.png", nextTolerance: 36 })).toBe(true);
    expect(shouldCancelSmartPreview({ ...current, nextMode: "color", nextImageKey: "frame-1.png", nextTolerance: 52 })).toBe(true);
  });

  it("does not request cancellation when no preview is active", () => {
    expect(
      shouldCancelSmartPreview({
        hasPreview: false,
        previousMode: "color",
        nextMode: "erase",
        previousImageKey: "frame-1.png",
        nextImageKey: "frame-2.png",
        previousTolerance: 36,
        nextTolerance: 52
      })
    ).toBe(false);
  });

  it("uses only keyed frames for refine preview and never falls back to raw green-screen frames", () => {
    expect(keyedPreviewPath({ keyed_path: "frames/keyed/frame_000000.png" })).toBe("frames/keyed/frame_000000.png");
    expect(keyedPreviewPath({ keyed_path: null })).toBeNull();
    expect(keyedPreviewPath(null)).toBeNull();
  });
});
