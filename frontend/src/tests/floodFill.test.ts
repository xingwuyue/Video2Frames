import { describe, expect, it } from "vitest";
import { connectedColorMask } from "../utils/floodFill";

function rgbaPixels(colors: Array<[number, number, number, number]>): Uint8ClampedArray {
  return new Uint8ClampedArray(colors.flat());
}

describe("connectedColorMask", () => {
  it("returns only the same-color island connected to the clicked pixel", () => {
    const data = rgbaPixels([
      [0, 255, 0, 255],
      [0, 255, 0, 255],
      [0, 0, 0, 255],
      [255, 0, 0, 255],
      [255, 0, 0, 255],
      [0, 0, 0, 255],
      [0, 0, 0, 255],
      [0, 255, 0, 255],
      [0, 0, 0, 255]
    ]);

    const before = new Uint8ClampedArray(data);
    const mask = connectedColorMask(data, 3, 3, 0, 0, 0);

    expect(Array.from(mask)).toEqual([1, 1, 0, 0, 0, 0, 0, 0, 0]);
    expect(data).toEqual(before);
  });

  it("returns an empty mask for out-of-bounds clicks", () => {
    const data = rgbaPixels([
      [0, 255, 0, 255],
      [0, 255, 0, 255],
      [0, 255, 0, 255],
      [0, 255, 0, 255]
    ]);

    expect(Array.from(connectedColorMask(data, 2, 2, -1, 0, 0))).toEqual([0, 0, 0, 0]);
    expect(Array.from(connectedColorMask(data, 2, 2, 2, 1, 0))).toEqual([0, 0, 0, 0]);
  });

  it("rejects negative tolerance", () => {
    const data = rgbaPixels([[0, 255, 0, 255]]);

    expect(() => connectedColorMask(data, 1, 1, 0, 0, -1)).toThrow("tolerance");
  });
});
