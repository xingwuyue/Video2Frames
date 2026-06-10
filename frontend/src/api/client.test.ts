import { afterEach, describe, expect, test, vi } from "vitest";
import { createProject, exportProject, importVideo, projectFileUrl } from "./client";
import type { ExportConfig } from "./types";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("api client", () => {
  test("throws backend error messages from non-ok responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ error: "项目不存在。" }), {
          status: 404,
          headers: { "Content-Type": "application/json" }
        })
      )
    );

    await expect(createProject("missing")).rejects.toThrow("项目不存在。");
  });

  test("throws backend error messages from ok responses", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ error: "bad" })));

    await expect(createProject("walk")).rejects.toThrow("bad");
  });

  test("rejects ok responses with invalid json", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response("not-json", {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
    );

    await expect(createProject("walk")).rejects.toThrow("API 响应格式无效。");
  });

  test("uses fallback status messages for non-ok invalid json responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response("not-json", {
          status: 500,
          headers: { "Content-Type": "application/json" }
        })
      )
    );

    await expect(createProject("walk")).rejects.toThrow("请求失败，状态码 500");
  });

  test("returns export results from successful responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          sheet: "projects/walk/exports/sheet.png",
          metadata: "projects/walk/exports/frames.json"
        })
      )
    );

    await expect(exportProject("walk")).resolves.toEqual({
      sheet: "projects/walk/exports/sheet.png",
      metadata: "projects/walk/exports/frames.json"
    });
  });

  test("sends export config in export requests", async () => {
    const fetch = vi.fn(async () =>
      Response.json({
        sheet: "projects/walk/exports/sheet.png",
        metadata: "projects/walk/exports/frames.json"
      })
    );
    vi.stubGlobal("fetch", fetch);
    const config: Partial<ExportConfig> = {
      auto_layout: true,
      rows: 1,
      columns: 6,
      max_columns: 6,
      cell_width: 352,
      cell_height: 352,
      fps: 12,
      center_x: 176,
      baseline_y: 320,
      target_body_height: 200,
      height_top_y: 120,
      alpha_threshold: 20,
      min_pixels_per_row: 3,
      soft_width_limit: 340,
      shared_scale_enabled: true,
      per_frame_scale_enabled: false,
      width_constraint_enabled: false
    };

    await exportProject("walk", config);

    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8765/api/projects/walk/export",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config)
      })
    );
  });

  test("uploads video bytes with filename and sample interval headers", async () => {
    const fetch = vi.fn(async () =>
      Response.json({
        name: "walk",
        root: "projects/walk",
        source_video: "source/walk.mp4",
        sample_every_n_frames: 2,
        background: {},
        export: {},
        frames: []
      })
    );
    vi.stubGlobal("fetch", fetch);
    const file = new File(["video-bytes"], "walk.mp4", { type: "video/mp4" });

    await importVideo("walk", file, 2);

    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8765/api/projects/walk/import/video",
      expect.objectContaining({
        method: "POST",
        body: file,
        headers: {
          "Content-Type": "video/mp4",
          "X-Filename": "walk.mp4",
          "X-Sample-Every-N-Frames": "2"
        }
      })
    );
  });

  test("builds project file urls for frame preview images", () => {
    expect(projectFileUrl("walk cycle", "frames/raw/frame 000001.png")).toBe(
      "http://127.0.0.1:8765/api/projects/walk%20cycle/files/frames/raw/frame%20000001.png"
    );
  });
});
