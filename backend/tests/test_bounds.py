from PIL import Image

from app.services.bounds import alpha_bounds


def test_alpha_bounds_returns_visible_extent_size():
    image = Image.new("RGBA", (6, 5), (0, 0, 0, 0))
    for y in range(1, 4):
        for x in range(2, 5):
            image.putpixel((x, y), (255, 0, 0, 255))

    assert alpha_bounds(image) == {"x": 2, "y": 1, "w": 3, "h": 3}


def test_alpha_bounds_returns_none_for_fully_transparent_image():
    image = Image.new("RGBA", (3, 3), (0, 0, 0, 0))

    assert alpha_bounds(image) is None
