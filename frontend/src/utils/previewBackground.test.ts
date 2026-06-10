import { describe, expect, it } from "vitest";
import { previewBackgroundModes } from "./previewBackground";

describe("previewBackgroundModes", () => {
  it("uses a single magenta inspection color instead of a split red purple background", () => {
    expect(previewBackgroundModes).toContainEqual({ value: "magenta", label: "品红底" });
    expect(previewBackgroundModes).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ value: "red-purple" })])
    );
  });
});
