import numpy as np
from PIL import Image


def alpha_bounds(image: Image.Image) -> dict[str, int] | None:
    rgba = image.convert("RGBA")
    alpha = np.asarray(rgba)[:, :, 3]
    visible_y, visible_x = np.nonzero(alpha)

    if visible_x.size == 0:
        return None

    min_x = int(visible_x.min())
    max_x = int(visible_x.max())
    min_y = int(visible_y.min())
    max_y = int(visible_y.max())
    return {
        "x": min_x,
        "y": min_y,
        "w": max_x - min_x + 1,
        "h": max_y - min_y + 1,
    }
