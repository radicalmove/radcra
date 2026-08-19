#!/usr/bin/env python3
"""Generate deterministic RGBA PNG icons for the Sphere extension."""

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


SIZES = (16, 48, 128)
BASE_SIZE = 128
SCALE = 4
# Sphere's approved blue ramp.  The transparent canvas keeps the mark safe for
# Chrome's light and dark browser surfaces without introducing a background
# colour outside the product palette.
INK = (12, 68, 124, 255)       # #0C447C
PRIMARY = (24, 95, 165, 255)   # #185FA5
ACTION = (55, 138, 221, 255)   # #378ADD
WHITE = (255, 255, 255, 255)
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "extension" / "public" / "icons"


def scaled_box(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return tuple(value * SCALE for value in box)


def draw_master_icon() -> Image.Image:
    """Return the 128px Sphere master, rendered at 4x for clean edges.

    The outer disk is the sphere; a pair of geometric latitude/longitude
    bands gives it depth.  The short white pill and tiny tail are a restrained
    course-review comment cue, not a generic chat-bubble logo.
    """
    image = Image.new("RGBA", (BASE_SIZE * SCALE, BASE_SIZE * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Keep every non-transparent pixel on the exact 96x96 safe-area artboard.
    draw.ellipse(scaled_box((16, 16, 112, 112)), fill=INK)
    draw.ellipse(scaled_box((20, 20, 108, 108)), fill=PRIMARY)

    # Angular highlight / longitude band: the mark remains geometric at 16px.
    draw.pieslice(scaled_box((27, 22, 101, 106)), start=204, end=324, fill=ACTION)
    draw.arc(scaled_box((30, 24, 98, 104)), start=116, end=246, fill=WHITE, width=3 * SCALE)
    draw.arc(scaled_box((25, 30, 103, 96)), start=258, end=72, fill=ACTION, width=3 * SCALE)

    # Restrained comment cue: a single white review note and a small tail.
    draw.rounded_rectangle(scaled_box((43, 56, 85, 70)), radius=6 * SCALE, fill=WHITE)
    draw.polygon(
        [(51 * SCALE, 68 * SCALE), (47 * SCALE, 78 * SCALE), (61 * SCALE, 69 * SCALE)],
        fill=WHITE,
    )
    image = image.resize((BASE_SIZE, BASE_SIZE), Image.Resampling.LANCZOS)
    # Lanczos preserves a soft edge but can leave faint ringing beyond the
    # logical artboard. Clip only that transparent fringe so the checked-in
    # master has the documented exact alpha safe area.
    safe_area = Image.new("L", image.size, 0)
    ImageDraw.Draw(safe_area).rectangle((16, 16, 111, 111), fill=255)
    image.putalpha(ImageChops.multiply(image.getchannel("A"), safe_area))
    return image


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
