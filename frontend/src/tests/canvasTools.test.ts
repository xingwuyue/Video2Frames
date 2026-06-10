import { describe, expect, it } from "vitest";
import { fitToViewport } from "../utils/canvasTools";

describe("fitToViewport", () => {
  it("returns the largest scale that fits while preserving aspect ratio", () => {
    expect(fitToViewport(400, 200, 100, 100)).toBe(0.25);
    expect(fitToViewport(200, 400, 100, 100)).toBe(0.25);
    expect(fitToViewport(320, 180, 640, 360)).toBe(2);
  });

  it("rejects zero and negative dimensions", () => {
    expect(() => fitToViewport(0, 100, 100, 100)).toThrow("dimensions");
    expect(() => fitToViewport(100, 100, -1, 100)).toThrow("dimensions");
  });
});
