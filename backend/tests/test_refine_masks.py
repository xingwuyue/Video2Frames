import pytest
from PIL import Image

from app.services.refine_masks import connected_color_erase


def image_pixels(image):
    return [image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)]


def test_connected_color_erase_only_removes_connected_similar_pixels():
    image = Image.new("RGBA", (5, 5), (255, 0, 0, 255))
    left_island = [(0, 1), (1, 1), (1, 2)]
    right_island = [(3, 1), (4, 1), (3, 2)]
    for point in left_island + right_island:
        image.putpixel(point, (0, 255, 0, 255))

    erased = connected_color_erase(image, 0, 1, 10)

    for point in left_island:
        assert erased.getpixel(point) == (0, 255, 0, 0)
    for point in right_island:
        assert erased.getpixel(point) == (0, 255, 0, 255)
    assert erased.getpixel((2, 1)) == (255, 0, 0, 255)


def test_connected_color_erase_preserves_outside_region_and_does_not_mutate_input():
    image = Image.new("RGBA", (3, 1), (0, 255, 0, 255))
    image.putpixel((1, 0), (255, 0, 0, 120))
    image.putpixel((2, 0), (0, 0, 255, 0))
    original_pixels = image_pixels(image)

    erased = connected_color_erase(image, 0, 0, 10)

    assert erased.getpixel((0, 0)) == (0, 255, 0, 0)
    assert erased.getpixel((1, 0)) == (255, 0, 0, 120)
    assert erased.getpixel((2, 0)) == (0, 0, 255, 0)
    assert image_pixels(image) == original_pixels


def test_connected_color_erase_rejects_negative_tolerance():
    image = Image.new("RGBA", (1, 1), (0, 255, 0, 255))

    with pytest.raises(ValueError):
        connected_color_erase(image, 0, 0, -1)


@pytest.mark.parametrize("start_x,start_y", [(-1, 0), (0, -1), (5, 0), (0, 5)])
def test_connected_color_erase_rejects_out_of_bounds_start(start_x, start_y):
    image = Image.new("RGBA", (5, 5), (0, 255, 0, 255))

    with pytest.raises(ValueError):
        connected_color_erase(image, start_x, start_y, 10)
