from collections import deque

from PIL import Image


def connected_color_erase(
    image: Image.Image, start_x: int, start_y: int, tolerance: int
) -> Image.Image:
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative")

    erased = image.convert("RGBA")
    width, height = erased.size
    if not (0 <= start_x < width and 0 <= start_y < height):
        raise ValueError("Start point is out of bounds")

    pixels = erased.load()
    key_r, key_g, key_b, _ = pixels[start_x, start_y]
    tolerance_squared = tolerance * tolerance
    visited = {(start_x, start_y)}
    queue = deque([(start_x, start_y)])

    while queue:
        x, y = queue.popleft()
        red, green, blue, _ = pixels[x, y]
        distance_squared = (
            (red - key_r) ** 2 + (green - key_g) ** 2 + (blue - key_b) ** 2
        )
        if distance_squared > tolerance_squared:
            continue

        pixels[x, y] = (red, green, blue, 0)

        for next_x, next_y in (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ):
            if (
                0 <= next_x < width
                and 0 <= next_y < height
                and (next_x, next_y) not in visited
            ):
                visited.add((next_x, next_y))
                queue.append((next_x, next_y))

    return erased
