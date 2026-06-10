export function connectedColorMask(
  data: Uint8ClampedArray,
  width: number,
  height: number,
  x: number,
  y: number,
  tolerance: number
): Uint8Array {
  if (width <= 0 || height <= 0 || data.length !== width * height * 4) {
    throw new Error("RGBA data dimensions are invalid");
  }
  if (tolerance < 0) {
    throw new Error("tolerance must be zero or greater");
  }

  const mask = new Uint8Array(width * height);
  if (x < 0 || y < 0 || x >= width || y >= height) {
    return mask;
  }

  const startIndex = (y * width + x) * 4;
  const targetR = data[startIndex];
  const targetG = data[startIndex + 1];
  const targetB = data[startIndex + 2];
  const toleranceSquared = tolerance * tolerance;
  const visited = new Uint8Array(width * height);
  const stack: Array<[number, number]> = [[x, y]];

  while (stack.length > 0) {
    const next = stack.pop();
    if (!next) {
      continue;
    }

    const [currentX, currentY] = next;
    if (currentX < 0 || currentY < 0 || currentX >= width || currentY >= height) {
      continue;
    }

    const pixelIndex = currentY * width + currentX;
    if (visited[pixelIndex]) {
      continue;
    }
    visited[pixelIndex] = 1;

    const dataIndex = pixelIndex * 4;
    const redDelta = data[dataIndex] - targetR;
    const greenDelta = data[dataIndex + 1] - targetG;
    const blueDelta = data[dataIndex + 2] - targetB;
    const distanceSquared = redDelta * redDelta + greenDelta * greenDelta + blueDelta * blueDelta;
    if (distanceSquared > toleranceSquared) {
      continue;
    }

    mask[pixelIndex] = 1;
    stack.push([currentX + 1, currentY]);
    stack.push([currentX - 1, currentY]);
    stack.push([currentX, currentY + 1]);
    stack.push([currentX, currentY - 1]);
  }

  return mask;
}
