import cv2
import numpy as np
from PIL import Image


def apply_chroma_key(
    image: Image.Image,
    key_color: tuple[int, int, int],
    tolerance: int,
    spill_suppression: float = 0.75,
    edge_cleanup: int = 1,
    min_component_area: int = 32,
) -> Image.Image:
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative")
    if spill_suppression < 0:
        raise ValueError("Spill suppression must be non-negative")
    if edge_cleanup < 0:
        raise ValueError("Edge cleanup must be non-negative")
    if min_component_area < 0:
        raise ValueError("Minimum component area must be non-negative")

    keyed = image.convert("RGBA")
    rgba = np.array(keyed, dtype=np.uint8)
    source_rgb = rgba[:, :, :3].copy()
    rgb = source_rgb.astype(np.int32)
    source_alpha = rgba[:, :, 3]
    tolerance_squared = tolerance * tolerance

    key_r, key_g, key_b = key_color
    green_screen = _is_green_screen_key(key_color)
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    visible = source_alpha > 0
    distance_squared = (red - key_r) ** 2 + (green - key_g) ** 2 + (blue - key_b) ** 2
    background_mask = visible & (distance_squared <= tolerance_squared)

    if green_screen:
        background_mask |= visible & _green_fringe_mask(red, green, blue, tolerance)
        background_mask |= visible & _hsv_green_mask(source_rgb)

    rgba[:, :, 3] = np.where(background_mask, 0, source_alpha).astype(np.uint8)
    if green_screen and spill_suppression > 0:
        _suppress_green_spill_array(rgba, background_mask, min(1.0, spill_suppression))
    keyed = Image.fromarray(rgba, "RGBA").copy()
    source_pixels = [tuple(pixel) for pixel in source_rgb.reshape(-1, 3)]

    if green_screen and edge_cleanup:
        _remove_weak_green_edges(keyed, source_pixels, tolerance, passes=edge_cleanup)
    if min_component_area > 1:
        _remove_small_components(keyed, min_component_area)

    return keyed


def _is_green_screen_key(key_color: tuple[int, int, int]) -> bool:
    red, green, blue = key_color
    return green >= 180 and green >= red + 80 and green >= blue + 80


def _is_hsv_green(red: int, green: int, blue: int) -> bool:
    hsv = cv2.cvtColor(np.array([[[red, green, blue]]], dtype=np.uint8), cv2.COLOR_RGB2HSV)[0, 0]
    hue, saturation, value = (int(hsv[0]), int(hsv[1]), int(hsv[2]))
    if value < 55 or saturation < 45:
        return False
    if not 35 <= hue <= 95:
        return False
    return green >= max(red, blue) + 12


def _hsv_green_mask(source_rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    green = source_rgb[:, :, 1].astype(np.int16)
    strongest_non_green = np.maximum(source_rgb[:, :, 0], source_rgb[:, :, 2]).astype(np.int16)
    return (
        (value >= 55)
        & (saturation >= 45)
        & (hue >= 35)
        & (hue <= 95)
        & (green >= strongest_non_green + 12)
    )


def _is_green_fringe(red: int, green: int, blue: int, tolerance: int) -> bool:
    strongest_non_green = max(red, blue)
    dominance = green - strongest_non_green
    if green < 56:
        return False
    if dominance < _green_fringe_dominance_threshold(green, tolerance):
        return False
    return dominance / max(1, green) >= 0.34


def _green_fringe_mask(red: np.ndarray, green: np.ndarray, blue: np.ndarray, tolerance: int) -> np.ndarray:
    strongest_non_green = np.maximum(red, blue)
    dominance = green - strongest_non_green
    threshold = np.where(green < 115, max(28, int(tolerance * 0.6)), max(54, int(tolerance * 1.2)))
    return (green >= 56) & (dominance >= threshold) & ((dominance / np.maximum(1, green)) >= 0.34)


def _green_fringe_dominance_threshold(green: int, tolerance: int) -> int:
    if green < 115:
        return max(28, int(tolerance * 0.6))
    return max(54, int(tolerance * 1.2))


def _suppress_green_spill(red: int, green: int, blue: int, strength: float) -> tuple[int, int, int]:
    strongest_non_green = max(red, blue)
    spill = green - strongest_non_green
    if spill <= 12:
        return red, green, blue
    if spill / max(1, green) > 0.34:
        return red, green, blue

    target_green = strongest_non_green + round(spill * (1 - strength))
    return red, max(0, min(255, target_green)), blue


def _suppress_green_spill_array(rgba: np.ndarray, background_mask: np.ndarray, strength: float) -> None:
    rgb = rgba[:, :, :3].astype(np.int16)
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    strongest_non_green = np.maximum(red, blue)
    spill = green - strongest_non_green
    foreground = (rgba[:, :, 3] > 0) & ~background_mask
    spill_mask = foreground & (spill > 12) & ((spill / np.maximum(1, green)) <= 0.34)
    target_green = strongest_non_green + np.rint(spill * (1 - strength)).astype(np.int16)
    rgba[:, :, 1] = np.where(spill_mask, np.clip(target_green, 0, 255), rgba[:, :, 1]).astype(np.uint8)


def _remove_weak_green_edges(
    image: Image.Image,
    source_pixels: list[tuple[int, int, int]],
    tolerance: int,
    passes: int,
) -> None:
    pixels = image.load()
    width, height = image.size
    for _ in range(passes):
        to_clear = []
        for y in range(height):
            for x in range(width):
                if pixels[x, y][3] == 0:
                    continue
                red, green, blue = source_pixels[y * width + x]
                if _is_weak_green_fringe(red, green, blue, tolerance) and _touches_transparency(pixels, width, height, x, y):
                    to_clear.append((x, y))

        if not to_clear:
            return
        for x, y in to_clear:
            red, green, blue, _alpha = pixels[x, y]
            pixels[x, y] = (red, green, blue, 0)


def _is_weak_green_fringe(red: int, green: int, blue: int, tolerance: int) -> bool:
    red, green, blue = int(red), int(green), int(blue)
    strongest_non_green = max(red, blue)
    dominance = green - strongest_non_green
    if green < 72:
        return False
    return dominance >= max(20, int(tolerance * 0.45)) and dominance / max(1, green) >= 0.24


def _touches_transparency(pixels, width: int, height: int, x: int, y: int) -> bool:
    for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
        for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
            if neighbor_x == x and neighbor_y == y:
                continue
            if pixels[neighbor_x, neighbor_y][3] == 0:
                return True
    return False


def _remove_small_components(image: Image.Image, min_area: int) -> None:
    pixels = image.load()
    width, height = image.size
    visited = set()

    for y in range(height):
        for x in range(width):
            if (x, y) in visited or pixels[x, y][3] == 0:
                continue
            component = _collect_alpha_component(pixels, width, height, x, y, visited)
            if len(component) < min_area and _looks_like_compression_residue(pixels, component):
                for clear_x, clear_y in component:
                    red, green, blue, _alpha = pixels[clear_x, clear_y]
                    pixels[clear_x, clear_y] = (red, green, blue, 0)


def _collect_alpha_component(pixels, width: int, height: int, start_x: int, start_y: int, visited: set) -> list[tuple[int, int]]:
    component = []
    stack = [(start_x, start_y)]
    visited.add((start_x, start_y))

    while stack:
        x, y = stack.pop()
        component.append((x, y))
        for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if next_x < 0 or next_y < 0 or next_x >= width or next_y >= height:
                continue
            if (next_x, next_y) in visited or pixels[next_x, next_y][3] == 0:
                continue
            visited.add((next_x, next_y))
            stack.append((next_x, next_y))

    return component


def _looks_like_compression_residue(pixels, component: list[tuple[int, int]]) -> bool:
    for x, y in component:
        red, green, blue, alpha = pixels[x, y]
        red, green, blue, alpha = int(red), int(green), int(blue), int(alpha)
        if alpha < 250:
            return False
        if max(red, green, blue) - min(red, green, blue) >= 64:
            return False
    return True
