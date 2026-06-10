export function fitToViewport(
  imageWidth: number,
  imageHeight: number,
  viewportWidth: number,
  viewportHeight: number
): number {
  const dimensions = [imageWidth, imageHeight, viewportWidth, viewportHeight];
  if (dimensions.some((dimension) => !Number.isFinite(dimension) || dimension <= 0)) {
    throw new Error("dimensions must be greater than zero");
  }

  return Math.min(viewportWidth / imageWidth, viewportHeight / imageHeight);
}
