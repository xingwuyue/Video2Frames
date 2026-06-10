import { describe, expect, test } from "vitest";
import { firstVideoFile } from "./videoFiles";

describe("video file helpers", () => {
  test("returns the first supported video file", () => {
    const text = new File(["notes"], "notes.txt", { type: "text/plain" });
    const video = new File(["video"], "walk.MP4", { type: "" });

    expect(firstVideoFile([text, video])).toBe(video);
  });

  test("ignores unsupported files", () => {
    const text = new File(["notes"], "notes.txt", { type: "text/plain" });

    expect(firstVideoFile([text])).toBeNull();
  });
});
