#!/usr/bin/env python3
"""Generate deterministic RGBA PNG icons for the RADCRA extension."""

from pathlib import Path

from PIL import Image, ImageDraw


SIZES = (16, 48, 128)
BASE_SIZE = 128
SCALE = 4
TEAL = (40, 196, 194, 255)
DARK_TEAL = (11, 98, 97, 255)
WHITE = (255, 255, 255, 255)
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "extension" / "public" / "icons"


def scaled_box(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return tuple(value * SCALE for value in box)


def draw_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (BASE_SIZE * SCALE, BASE_SIZE * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(scaled_box((15, 13, 113, 93)), radius=25 * SCALE, fill=TEAL, outline=DARK_TEAL, width=5 * SCALE)
    draw.polygon([(53 * SCALE, 89 * SCALE), (47 * SCALE, 113 * SCALE), (77 * SCALE, 92 * SCALE)], fill=TEAL)
    draw.line([(53 * SCALE, 89 * SCALE), (47 * SCALE, 113 * SCALE), (77 * SCALE, 92 * SCALE)], fill=DARK_TEAL, width=5 * SCALE, joint="curve")
    for y in (39, 57, 75):
        draw.rounded_rectangle(scaled_box((36, y, 92, y + 7)), radius=3 * SCALE, fill=WHITE)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def verify_icon(path: Path, size: int) -> None:
    with Image.open(path) as icon:
        if icon.size != (size, size):
            raise RuntimeError(f"{path} must be {size}x{size}, got {icon.size}")
        if icon.mode != "RGBA" or icon.getbands() != ("R", "G", "B", "A"):
            raise RuntimeError(f"{path} must preserve an RGBA alpha channel")


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        path = OUTPUT_DIRECTORY / f"icon{size}.png"
        image = draw_icon(size)
        if image.size != (size, size) or image.mode != "RGBA":
            raise RuntimeError(f"generated icon{size}.png has invalid dimensions or alpha mode")
        image.save(path, format="PNG", optimize=False, compress_level=9)
        verify_icon(path, size)


if __name__ == "__main__":
    main()
