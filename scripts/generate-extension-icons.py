#!/usr/bin/env python3
"""Generate deterministic RGBA PNG icons for the RADCRA extension."""

import argparse
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


def draw_master_icon() -> Image.Image:
    image = Image.new("RGBA", (BASE_SIZE * SCALE, BASE_SIZE * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # The mark is drawn on a centered 96x96 logical artboard (16..112).
    draw.rounded_rectangle(scaled_box((19, 19, 109, 92)), radius=22 * SCALE, fill=TEAL, outline=DARK_TEAL, width=4 * SCALE)
    draw.polygon([(54 * SCALE, 87 * SCALE), (49 * SCALE, 107 * SCALE), (75 * SCALE, 90 * SCALE)], fill=TEAL)
    draw.line([(54 * SCALE, 87 * SCALE), (49 * SCALE, 107 * SCALE), (75 * SCALE, 90 * SCALE)], fill=DARK_TEAL, width=4 * SCALE, joint="curve")
    for y in (42, 58, 74):
        draw.rounded_rectangle(scaled_box((38, y, 90, y + 6)), radius=3 * SCALE, fill=WHITE)
    return image.resize((BASE_SIZE, BASE_SIZE), Image.Resampling.LANCZOS)


def verify_icon(path: Path, size: int) -> None:
    with Image.open(path) as icon:
        if icon.size != (size, size):
            raise RuntimeError(f"{path} must be {size}x{size}, got {icon.size}")
        if icon.mode != "RGBA" or icon.getbands() != ("R", "G", "B", "A"):
            raise RuntimeError(f"{path} must preserve an RGBA alpha channel")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path, default=OUTPUT_DIRECTORY)
    args = parser.parse_args()
    output_directory = args.output_directory
    output_directory.mkdir(parents=True, exist_ok=True)
    master = draw_master_icon()
    for size in SIZES:
        path = output_directory / f"icon{size}.png"
        image = master if size == BASE_SIZE else master.resize((size, size), Image.Resampling.LANCZOS)
        if image.size != (size, size) or image.mode != "RGBA":
            raise RuntimeError(f"generated icon{size}.png has invalid dimensions or alpha mode")
        image.save(path, format="PNG", optimize=False, compress_level=0)
        verify_icon(path, size)


if __name__ == "__main__":
    main()
