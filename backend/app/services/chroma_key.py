"""Green-screen chroma keying with YCbCr soft matte and morphological refinement.

Pipeline overview
─────────────────
1. Convert to YCbCr; compute per-pixel chroma distance to the key colour.
2. Build a continuous 0→1 soft alpha map (instead of a binary mask).
3. Morphological OPEN → CLOSE → GaussianBlur to clean noise and soften edges.
4. Edge-band refinement: detect the narrow transition zone and apply more
   aggressive green removal there.
5. Enhanced spill suppression on foreground pixels (fixes the old bug where
   high-spill pixels were *skipped*).
6. Small-component removal for compression artefacts.

Every step is fully vectorised with numpy / OpenCV — no per-pixel Python loops.
"""

import cv2
import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def apply_chroma_key(
    image: Image.Image,
    key_color: tuple[int, int, int],
    tolerance: int,
    spill_suppression: float = 0.75,
    edge_cleanup: int = 1,
    min_component_area: int = 32,
) -> Image.Image:
    """Remove green-screen background and return an RGBA image.

    Parameters
    ----------
    image : PIL Image
        Source frame (any mode — will be converted to RGBA).
    key_color : (R, G, B)
        Nominal chroma-key colour, e.g. ``(0, 255, 0)``.
    tolerance : int ≥ 0
        Controls how far from *key_color* a pixel can be and still be removed.
        Higher = more aggressive background removal.
    spill_suppression : float 0–1
        Strength of green-spill correction on foreground pixels.
    edge_cleanup : int ≥ 0
        Number of morphological refinement passes on the edge band.
    min_component_area : int ≥ 0
        Connected foreground blobs smaller than this are removed.
    """
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative")
    if spill_suppression < 0:
        raise ValueError("Spill suppression must be non-negative")
    if edge_cleanup < 0:
        raise ValueError("Edge cleanup must be non-negative")
    if min_component_area < 0:
        raise ValueError("Minimum component area must be non-negative")

    rgba = np.array(image.convert("RGBA"), dtype=np.uint8)
    source_alpha = rgba[:, :, 3].copy()
    rgb = rgba[:, :, :3]

    green_screen = _is_green_screen_key(key_color)

    if green_screen:
        soft_alpha = _build_soft_alpha_ycbcr(rgb, key_color, tolerance, source_alpha)
        soft_alpha = _morphological_refine(soft_alpha, edge_cleanup)
        soft_alpha = _edge_band_refine(rgb, soft_alpha, key_color, tolerance)
    else:
        # Fallback for non-green keys: simple RGB distance soft matte
        soft_alpha = _build_soft_alpha_rgb(rgb, key_color, tolerance, source_alpha)
        soft_alpha = _morphological_refine(soft_alpha, max(1, edge_cleanup))

    # Apply soft alpha
    rgba[:, :, 3] = soft_alpha

    # Spill suppression on remaining foreground
    if green_screen and spill_suppression > 0:
        _suppress_green_spill(rgba, min(1.0, spill_suppression))

    # Remove tiny isolated foreground blobs
    if min_component_area > 1:
        _remove_small_components_cv(rgba, min_component_area)

    return Image.fromarray(rgba, "RGBA")


# ---------------------------------------------------------------------------
# Green-screen detection
# ---------------------------------------------------------------------------

def _is_green_screen_key(key_color: tuple[int, int, int]) -> bool:
    red, green, blue = key_color
    return green >= 180 and green >= red + 80 and green >= blue + 80


# ---------------------------------------------------------------------------
# Soft alpha construction — YCbCr (green screens)
# ---------------------------------------------------------------------------

def _build_soft_alpha_ycbcr(
    rgb: np.ndarray,
    key_color: tuple[int, int, int],
    tolerance: int,
    source_alpha: np.ndarray,
) -> np.ndarray:
    """Build a continuous alpha map using chroma distance in YCbCr space."""
    # Convert source to YCbCr
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ycbcr = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb).astype(np.float32)

    # Convert key colour to YCbCr
    key_pixel = np.array([[[key_color[2], key_color[1], key_color[0]]]], dtype=np.uint8)
    key_ycbcr = cv2.cvtColor(key_pixel, cv2.COLOR_BGR2YCrCb).astype(np.float32)[0, 0]

    # Chroma distance (ignore luminance Y — only Cb/Cr matter)
    cb_dist = ycbcr[:, :, 1] - key_ycbcr[1]
    cr_dist = ycbcr[:, :, 2] - key_ycbcr[2]
    chroma_dist = np.sqrt(cb_dist ** 2 + cr_dist ** 2)

    # Two-band soft matte:
    #   dist < inner_tol  →  alpha = 0  (definitely background)
    #   dist > outer_tol  →  alpha = 255 (definitely foreground)
    #   between           →  linear ramp
    inner_tol = max(4.0, tolerance * 0.45)
    outer_tol = max(inner_tol + 6.0, tolerance * 1.1)

    alpha_f = np.clip((chroma_dist - inner_tol) / max(1.0, outer_tol - inner_tol), 0.0, 1.0)

    # Also incorporate HSV-based green detection for pixels that YCbCr might miss
    hsv_bg = _hsv_green_mask_wide(rgb)
    alpha_f = np.where(hsv_bg, np.minimum(alpha_f, 0.0), alpha_f)

    # Incorporate RGB distance check as additional safety net
    rgb_i = rgb.astype(np.float32)
    kr, kg, kb = float(key_color[0]), float(key_color[1]), float(key_color[2])
    rgb_dist = np.sqrt(
        (rgb_i[:, :, 0] - kr) ** 2
        + (rgb_i[:, :, 1] - kg) ** 2
        + (rgb_i[:, :, 2] - kb) ** 2
    )
    rgb_bg = rgb_dist < (tolerance * 0.85)
    alpha_f = np.where(rgb_bg, 0.0, alpha_f)

    # Green-dominant fringe detection
    green = rgb[:, :, 1].astype(np.int16)
    non_green = np.maximum(rgb[:, :, 0], rgb[:, :, 2]).astype(np.int16)
    dominance = green - non_green
    fringe = (green >= 50) & (dominance >= max(18, int(tolerance * 0.35))) & (dominance.astype(np.float32) / np.maximum(1, green).astype(np.float32) >= 0.28)
    alpha_f = np.where(fringe, np.minimum(alpha_f, 0.15), alpha_f)

    # Respect original transparency
    alpha_out = (alpha_f * 255).astype(np.uint8)
    alpha_out = np.minimum(alpha_out, source_alpha)
    return alpha_out


# ---------------------------------------------------------------------------
# Soft alpha construction — RGB fallback (non-green keys)
# ---------------------------------------------------------------------------

def _build_soft_alpha_rgb(
    rgb: np.ndarray,
    key_color: tuple[int, int, int],
    tolerance: int,
    source_alpha: np.ndarray,
) -> np.ndarray:
    """Simple RGB-distance soft matte for non-green key colours."""
    rgb_f = rgb.astype(np.float32)
    kr, kg, kb = float(key_color[0]), float(key_color[1]), float(key_color[2])
    dist = np.sqrt(
        (rgb_f[:, :, 0] - kr) ** 2
        + (rgb_f[:, :, 1] - kg) ** 2
        + (rgb_f[:, :, 2] - kb) ** 2
    )
    inner = max(3.0, tolerance * 0.6)
    outer = max(inner + 5.0, tolerance * 1.2)
    alpha_f = np.clip((dist - inner) / max(1.0, outer - inner), 0.0, 1.0)
    alpha_out = (alpha_f * 255).astype(np.uint8)
    return np.minimum(alpha_out, source_alpha)


# ---------------------------------------------------------------------------
# HSV wide-range green mask
# ---------------------------------------------------------------------------

def _hsv_green_mask_wide(rgb: np.ndarray) -> np.ndarray:
    """Wider HSV green detection than the old implementation."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    green = rgb[:, :, 1].astype(np.int16)
    non_green = np.maximum(rgb[:, :, 0], rgb[:, :, 2]).astype(np.int16)
    return (
        (val >= 40)
        & (sat >= 30)
        & (hue >= 30)
        & (hue <= 100)
        & (green >= non_green + 8)
    )


# ---------------------------------------------------------------------------
# Morphological refinement
# ---------------------------------------------------------------------------

def _morphological_refine(alpha: np.ndarray, passes: int) -> np.ndarray:
    """Clean up alpha with morphological operations and Gaussian blur.

    - OPEN: removes small foreground noise inside background areas
    - CLOSE: fills tiny holes inside foreground
    - GaussianBlur: softens the alpha edge for natural transitions
    """
    if passes <= 0:
        return alpha

    result = alpha.copy()

    # Convert to binary mask for morphological ops on hard edges
    _, binary = cv2.threshold(result, 127, 255, cv2.THRESH_BINARY)

    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    for _ in range(passes):
        # OPEN: erode→dilate — removes small bright spots (foreground noise in BG)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small)
        # CLOSE: dilate→erode — fills small dark spots (holes in foreground)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_medium)

    # Where the binary mask says "background" but the soft alpha had partial
    # opacity, clamp to zero.  Where binary says "foreground", keep the soft
    # alpha (preserving subtle gradients).
    result = np.where(binary == 0, 0, result).astype(np.uint8)

    # Gaussian blur to soften the alpha transition
    result = cv2.GaussianBlur(result, (3, 3), 0.8)

    return result


# ---------------------------------------------------------------------------
# Edge-band refinement
# ---------------------------------------------------------------------------

def _edge_band_refine(
    rgb: np.ndarray,
    alpha: np.ndarray,
    key_color: tuple[int, int, int],
    tolerance: int,
) -> np.ndarray:
    """Find the narrow foreground/background transition zone and apply
    more aggressive green removal there."""
    # Definite foreground / background
    fg_mask = (alpha > 200).astype(np.uint8)
    bg_mask = (alpha < 30).astype(np.uint8)

    # Dilate foreground and background to find the overlap band
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg_dilated = cv2.dilate(fg_mask, kernel, iterations=2)
    bg_dilated = cv2.dilate(bg_mask, kernel, iterations=2)

    edge_band = (fg_dilated & bg_dilated).astype(bool)

    if not np.any(edge_band):
        return alpha

    # In the edge band, apply stricter green detection
    green = rgb[:, :, 1].astype(np.int16)
    non_green = np.maximum(rgb[:, :, 0], rgb[:, :, 2]).astype(np.int16)
    dominance = green - non_green

    # Lower thresholds in the edge band
    edge_green = edge_band & (
        (green >= 40)
        & (dominance >= max(10, int(tolerance * 0.2)))
        & (dominance.astype(np.float32) / np.maximum(1, green).astype(np.float32) >= 0.18)
    )

    result = alpha.copy()
    # Strongly reduce alpha for green-ish edge pixels
    result[edge_green] = np.minimum(result[edge_green], (result[edge_green] * 0.15).astype(np.uint8))

    # Additional: for any pixel in edge band that is mildly green, reduce alpha
    mild_green = edge_band & (dominance >= max(5, int(tolerance * 0.1))) & (green >= 30)
    damping = np.clip(1.0 - dominance.astype(np.float32) / max(1, tolerance * 0.8), 0.0, 1.0)
    result = np.where(
        mild_green,
        np.clip(result.astype(np.float32) * damping, 0, 255).astype(np.uint8),
        result,
    )

    return result


# ---------------------------------------------------------------------------
# Enhanced spill suppression
# ---------------------------------------------------------------------------

def _suppress_green_spill(rgba: np.ndarray, strength: float) -> None:
    """Remove green colour cast from foreground pixels.

    Fixed bug: the old implementation *skipped* pixels where
    ``spill / green > 0.34`` — exactly the pixels that need the most correction.
    """
    fg_mask = rgba[:, :, 3] > 0
    if not np.any(fg_mask):
        return

    rgb = rgba[:, :, :3].astype(np.float32)
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    non_green = np.maximum(red, blue)
    spill = green - non_green

    # Any foreground pixel with green > max(red, blue) by more than a threshold
    needs_correction = fg_mask & (spill > 6)

    if not np.any(needs_correction):
        return

    # Compute corrected green channel
    corrected_green = non_green + spill * (1.0 - strength)
    corrected_green = np.clip(corrected_green, 0, 255)

    # Slight boost to red/blue to compensate for removed green energy
    # This prevents the corrected areas from looking unnaturally dark
    compensation = spill * strength * 0.12
    corrected_red = np.clip(red + compensation, 0, 255)
    corrected_blue = np.clip(blue + compensation, 0, 255)

    rgba[:, :, 0] = np.where(needs_correction, corrected_red, red).astype(np.uint8)
    rgba[:, :, 1] = np.where(needs_correction, corrected_green, green).astype(np.uint8)
    rgba[:, :, 2] = np.where(needs_correction, corrected_blue, blue).astype(np.uint8)


# ---------------------------------------------------------------------------
# Small-component removal (vectorised with OpenCV connected components)
# ---------------------------------------------------------------------------

def _remove_small_components_cv(rgba: np.ndarray, min_area: int) -> None:
    """Remove small connected foreground blobs using OpenCV.

    Replaces the old per-pixel BFS with a single ``cv2.connectedComponentsWithStats``
    call — orders of magnitude faster on large images.
    """
    alpha = rgba[:, :, 3]
    binary = (alpha > 0).astype(np.uint8)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=4)

    for label_id in range(1, num_labels):
        area = stats[label_id, cv2.CC_STAT_AREA]
        if area >= min_area:
            continue

        # Check if this blob looks like compression residue
        component_mask = labels == label_id
        component_alpha = alpha[component_mask]
        component_rgb = rgba[:, :, :3][component_mask]

        # All pixels nearly opaque and low colour variance → residue
        if np.all(component_alpha >= 250):
            channel_range = component_rgb.max(axis=0).astype(int) - component_rgb.min(axis=0).astype(int)
            if np.all(channel_range < 64):
                alpha[component_mask] = 0

    rgba[:, :, 3] = alpha
