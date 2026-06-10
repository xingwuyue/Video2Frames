import { describe, expect, it } from "vitest";
import { advancePlaybackFrame, playbackFrameIds, previousPlaybackFrame } from "./playback";

describe("playback helpers", () => {
  it("uses only enabled visible frames", () => {
    const frames = [{ id: "01" }, { id: "02" }, { id: "03" }, { id: "04" }];

    expect(
      playbackFrameIds(frames, new Set(["01", "02", "03"]), new Set(["02"]), new Set(["04"]))
    ).toEqual(["01", "03"]);
  });

  it("advances and stops at the last frame when looping is off", () => {
    expect(advancePlaybackFrame(["01", "02"], "01", false)).toEqual({
      frameId: "02",
      shouldStop: false
    });
    expect(advancePlaybackFrame(["01", "02"], "02", false)).toEqual({
      frameId: "02",
      shouldStop: true
    });
  });

  it("wraps forward and backward when looping is on", () => {
    expect(advancePlaybackFrame(["01", "02"], "02", true)).toEqual({
      frameId: "01",
      shouldStop: false
    });
    expect(previousPlaybackFrame(["01", "02"], "01", true)).toBe("02");
  });
});
