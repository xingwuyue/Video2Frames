import { describe, expect, it, vi } from "vitest";
import {
  collectExportResultPaths,
  createDefaultExportConfig,
  createExportRequestConfig,
  runGuardedExport,
  validateExportCapacity
} from "../components/ExportPanel";

const capacityError = "帧数超过当前行列容量，请增加行列或删除帧。";
const defaultConfig = createDefaultExportConfig();
const defaultRequestConfig = createExportRequestConfig(defaultConfig);

describe("validateExportCapacity", () => {
  it("blocks export when manual layout enabled frames exceed rows by columns capacity", () => {
    expect(validateExportCapacity({ auto_layout: false, rows: 2, columns: 2, enabledFrameCount: 5 })).toBe(capacityError);
  });

  it("allows export when manual layout capacity can hold enabled frames", () => {
    expect(validateExportCapacity({ auto_layout: false, rows: 2, columns: 3, enabledFrameCount: 5 })).toBeNull();
  });

  it("allows auto layout export beyond initial rows by columns capacity", async () => {
    const exportProject = vi.fn(async () => ({
      sheet: "projects/walk/exports/sheet.png",
      metadata: "projects/walk/exports/frames.json"
    }));

    const result = await runGuardedExport({
      projectName: "walk",
      auto_layout: true,
      rows: 1,
      columns: 6,
      enabledFrameCount: 7,
      config: defaultRequestConfig,
      exportProject
    });

    expect(result).toEqual({
      ok: true,
      result: {
        sheet: "projects/walk/exports/sheet.png",
        metadata: "projects/walk/exports/frames.json"
      }
    });
    expect(exportProject).toHaveBeenCalledWith("walk", defaultRequestConfig);
  });

  it("does not call export when manual layout enabled frames exceed capacity", async () => {
    const exportProject = vi.fn(async () => ({
      sheet: "projects/walk/exports/sheet.png",
      metadata: "projects/walk/exports/frames.json"
    }));

    const result = await runGuardedExport({
      projectName: "walk",
      auto_layout: false,
      rows: 2,
      columns: 2,
      enabledFrameCount: 5,
      config: createExportRequestConfig({ ...defaultConfig, auto_layout: false, rows: 2, columns: 2 }),
      exportProject
    });

    expect(result).toEqual({
      ok: false,
      error: capacityError
    });
    expect(exportProject).not.toHaveBeenCalled();
  });

  it("shows only paths returned by the export API", () => {
    expect(
      collectExportResultPaths({
        sheet: "projects/walk/exports/sheet.png",
        metadata: "projects/walk/exports/frames.json"
      })
    ).toEqual([
      { label: "sheet.png", value: "projects/walk/exports/sheet.png" },
      { label: "frames.json", value: "projects/walk/exports/frames.json" }
    ]);
  });

  it("uses V2 export defaults", () => {
    expect(createDefaultExportConfig()).toMatchObject({
      auto_layout: true,
      rows: 1,
      columns: 6,
      max_columns: 6,
      cell_width: 352,
      cell_height: 352,
      center_x: 176,
      baseline_y: 320,
      target_body_height: 200
    });
  });

  it("omits unsupported export toggles from backend request config", () => {
    expect(createExportRequestConfig(defaultConfig)).not.toHaveProperty("include_frames");
    expect(createExportRequestConfig(defaultConfig)).not.toHaveProperty("include_godot_helper");
  });
});
