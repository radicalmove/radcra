#!/usr/bin/env python3
"""Generate deterministic, first-party Sphere promotional artwork."""

import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "store-assets" / "sphere-promo-440x280.png"
ICON = ROOT / "extension" / "public" / "icons" / "icon128.png"
SCALE = 4
PRIMARY = (24, 95, 165)
INK = (12, 68, 124)
ACTION = (55, 138, 221)
GROUND = (244, 249, 255)
WHITE = (255, 255, 255)
FONT = ROOT / "store-assets" / "source" / "DejaVuSans-Bold.ttf"
FONT_SHA256 = "e6476c1b80502924294eed40894c5b18e06c181444ca953e5334262df9c27724"


def resolve_font() -> Path:
    if not FONT.is_file():
        raise RuntimeError(f"Bundled font is required: {FONT}")
    digest = hashlib.sha256(FONT.read_bytes()).hexdigest()
    if digest != FONT_SHA256:
        raise RuntimeError(f"Bundled font has unexpected SHA-256: {digest}")
    return FONT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    font_path = resolve_font()
    canvas = Image.new("RGB", (440 * SCALE, 280 * SCALE), GROUND)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((20 * SCALE, 20 * SCALE, 420 * SCALE, 260 * SCALE), radius=28 * SCALE, fill=PRIMARY)
    draw.ellipse((365 * SCALE, 31 * SCALE, 393 * SCALE, 59 * SCALE), fill=ACTION)

    with Image.open(ICON) as source:
        icon = source.convert("RGBA").resize((144 * SCALE, 144 * SCALE), Image.Resampling.LANCZOS)
    canvas.paste(icon, (31 * SCALE, 68 * SCALE), icon)

    title_font = ImageFont.truetype(str(font_path), 48 * SCALE)
    subtitle_font = ImageFont.truetype(str(font_path), 18 * SCALE)
    draw.text((181 * SCALE, 91 * SCALE), "Sphere", font=title_font, fill=WHITE, stroke_width=0)
    draw.rounded_rectangle((183 * SCALE, 153 * SCALE, 384 * SCALE, 158 * SCALE), radius=2 * SCALE, fill=ACTION)
    draw.text((183 * SCALE, 171 * SCALE), "Course Review App", font=subtitle_font, fill=WHITE)

    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.resize((440, 280), Image.Resampling.LANCZOS).save(
        output, format="PNG", optimize=False, compress_level=0
    )


if __name__ == "__main__":
    main()
