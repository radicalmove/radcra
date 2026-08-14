#!/usr/bin/env python3
"""Generate deterministic, first-party RADCRA promotional artwork."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "store-assets" / "radcra-promo-440x280.png"
ICON = ROOT / "extension" / "public" / "icons" / "icon128.png"
SCALE = 4
TEAL = (40, 196, 194)
DARK_TEAL = (11, 78, 78)
RED = (221, 67, 68)
CREAM = (247, 252, 251)
FONT = ROOT / "store-assets" / "source" / "DejaVuSans-Bold.ttf"


def resolve_font() -> Path:
    if not FONT.is_file():
        raise RuntimeError(f"Bundled font is required: {FONT}")
    return FONT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    font_path = resolve_font()
    canvas = Image.new("RGB", (440 * SCALE, 280 * SCALE), CREAM)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((20 * SCALE, 20 * SCALE, 420 * SCALE, 260 * SCALE), radius=28 * SCALE, fill=TEAL)
    draw.ellipse((367 * SCALE, 31 * SCALE, 391 * SCALE, 55 * SCALE), fill=RED)

    with Image.open(ICON) as source:
        icon = source.convert("RGBA").resize((144 * SCALE, 144 * SCALE), Image.Resampling.LANCZOS)
    canvas.paste(icon, (31 * SCALE, 68 * SCALE), icon)

    title_font = ImageFont.truetype(str(font_path), 48 * SCALE)
    subtitle_font = ImageFont.truetype(str(font_path), 18 * SCALE)
    draw.text((181 * SCALE, 91 * SCALE), "RADCRA", font=title_font, fill=DARK_TEAL, stroke_width=0)
    draw.rounded_rectangle((183 * SCALE, 153 * SCALE, 384 * SCALE, 158 * SCALE), radius=2 * SCALE, fill=RED)
    draw.text((183 * SCALE, 171 * SCALE), "Course Review App", font=subtitle_font, fill=DARK_TEAL)

    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.resize((440, 280), Image.Resampling.LANCZOS).save(
        output, format="PNG", optimize=False, compress_level=9
    )


if __name__ == "__main__":
    main()
