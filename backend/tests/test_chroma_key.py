import pytest
from PIL import Image

from app.services.chroma_key import apply_chroma_key


def image_pixels(image):
    return [image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)]


def test_chroma_key_removes_green_and_preserves_red_square():
    image = Image.new("RGB", (4, 4), (0, 255, 0))
    for y in range(1, 3):
        for x in range(1, 3):
            image.putpixel((x, y), (255, 0, 0))

    keyed = apply_chroma_key(image, (0, 255, 0), 10)

    assert keyed.mode == "RGBA"
    for y in range(4):
        for x in range(4):
            pixel = keyed.getpixel((x, y))
            if 1 <= x <= 2 and 1 <= y <= 2:
                assert pixel == (255, 0, 0, 255)
            else:
                assert pixel == (0, 255, 0, 0)


def test_chroma_key_preserves_source_alpha_and_does_not_mutate_input():
    image = Image.new("RGBA", (3, 1), (0, 255, 0, 255))
    image.putpixel((1, 0), (255, 0, 0, 120))
    image.putpixel((2, 0), (0, 0, 255, 0))
    original_pixels = image_pixels(image)

    keyed = apply_chroma_key(image, (0, 255, 0), 10)

    assert keyed.getpixel((0, 0)) == (0, 255, 0, 0)
    assert keyed.getpixel((1, 0)) == (255, 0, 0, 120)
    assert keyed.getpixel((2, 0)) == (0, 0, 255, 0)
    assert image_pixels(image) == original_pixels


def test_chroma_key_removes_green_dominant_fringe_outside_distance_tolerance():
    image = Image.new("RGBA", (3, 1), (0, 0, 0, 0))
    image.putpixel((0, 0), (32, 188, 22, 255))
    image.putpixel((1, 0), (28, 62, 105, 255))
    image.putpixel((2, 0), (178, 125, 88, 255))

    keyed = apply_chroma_key(image, (0, 255, 0), 45)

    assert keyed.getpixel((0, 0))[3] == 0
    assert keyed.getpixel((1, 0)) == (28, 62, 105, 255)
    assert keyed.getpixel((2, 0)) == (178, 125, 88, 255)


def test_chroma_key_removes_dark_green_outline_without_deleting_dark_blue_clothing():
    image = Image.new("RGBA", (3, 1), (0, 0, 0, 0))
    image.putpixel((0, 0), (9, 86, 12, 255))
    image.putpixel((1, 0), (24, 48, 96, 255))
    image.putpixel((2, 0), (34, 40, 35, 255))

    keyed = apply_chroma_key(image, (0, 255, 0), 45)

    assert keyed.getpixel((0, 0))[3] == 0
    assert keyed.getpixel((1, 0)) == (24, 48, 96, 255)
    assert keyed.getpixel((2, 0)) == (34, 40, 35, 255)


def test_chroma_key_suppresses_green_spill_on_preserved_edge_pixels():
    image = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
    image.putpixel((0, 0), (205, 244, 207, 255))
    image.putpixel((1, 0), (38, 52, 122, 255))

    keyed = apply_chroma_key(image, (0, 255, 0), 45, spill_suppression=0.75)

    red, green, blue, alpha = keyed.getpixel((0, 0))
    assert alpha == 255
    assert green <= max(red, blue) + 12
    assert keyed.getpixel((1, 0)) == (38, 52, 122, 255)


def test_chroma_key_removes_single_pixel_compression_noise_after_keying():
    image = Image.new("RGBA", (5, 5), (0, 255, 0, 255))
    for y in range(1, 4):
        for x in range(1, 4):
            image.putpixel((x, y), (255, 0, 0, 255))
    image.putpixel((4, 4), (82, 104, 71, 255))

    keyed = apply_chroma_key(image, (0, 255, 0), 45)

    assert keyed.getpixel((4, 4))[3] == 0
    assert keyed.getpixel((2, 2)) == (255, 0, 0, 255)


def test_chroma_key_removes_weak_green_edge_pixels_touching_transparency():
    image = Image.new("RGBA", (5, 5), (0, 255, 0, 255))
    for y in range(1, 4):
        for x in range(1, 4):
            image.putpixel((x, y), (255, 0, 0, 255))
    image.putpixel((1, 2), (92, 137, 84, 255))

    keyed = apply_chroma_key(image, (0, 255, 0), 45)

    assert keyed.getpixel((1, 2))[3] == 0
    assert keyed.getpixel((2, 2)) == (255, 0, 0, 255)


def test_chroma_key_removes_hsv_green_background_when_rgb_distance_is_not_close():
    image = Image.new("RGBA", (3, 3), (70, 145, 120, 255))
    image.putpixel((1, 1), (220, 30, 30, 255))

    keyed = apply_chroma_key(image, (0, 255, 0), 45)

    assert keyed.getpixel((0, 0))[3] == 0
    assert keyed.getpixel((1, 1)) == (220, 30, 30, 255)


def test_chroma_key_removes_larger_low_chroma_residue_component():
    image = Image.new("RGBA", (8, 8), (0, 255, 0, 255))
    for y in range(1, 6):
        for x in range(1, 6):
            image.putpixel((x, y), (255, 0, 0, 255))
    for y in range(6, 8):
        for x in range(6, 8):
            image.putpixel((x, y), (88, 106, 84, 255))

    keyed = apply_chroma_key(image, (0, 255, 0), 45)

    assert keyed.getpixel((6, 6))[3] == 0
    assert keyed.getpixel((3, 3)) == (255, 0, 0, 255)


def test_chroma_key_rejects_negative_tolerance():
    image = Image.new("RGBA", (1, 1), (0, 255, 0, 255))

    with pytest.raises(ValueError):
        apply_chroma_key(image, (0, 255, 0), -1)
