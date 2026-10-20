#!/usr/bin/env python3
"""Milo V0.01: screenshot the main display with a labeled 31x31 grid overlay."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GRID_SIZE = 31
FONT_PATH = "/System/Library/Fonts/SFNS.ttf"


def capture_screen() -> Image.Image:
    """Capture the main Mac display using the built-in screencapture tool."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        screenshot_path = Path(tmp_dir) / "screen.png"
        result = subprocess.run(
            ["screencapture", "-x", "-m", str(screenshot_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0 or not screenshot_path.exists():
            detail = result.stderr.strip() or "screencapture produced no image."
            raise RuntimeError(
                "Could not capture the screen. Grant Screen Recording permission "
                f"to your terminal in System Settings > Privacy & Security. ({detail})"
            )

        return Image.open(screenshot_path).convert("RGB")


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default(size=size)


def column_label(index: int) -> str:
    """Convert a 1-based column index to A, B, ..., Z, AA, AB, ..."""
    label = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label


def draw_grid(image: Image.Image) -> Image.Image:
    """Overlay a 31x31 grid with spreadsheet-style coordinates."""
    width, height = image.size
    draw = ImageDraw.Draw(image)
    cell_width = width / GRID_SIZE
    cell_height = height / GRID_SIZE
    line_width = max(1, round(min(width, height) / 500))
    line_color = (255, 0, 0)
    font_size = max(8, round(min(cell_width, cell_height) / 5))
    font = load_font(font_size)
    padding = max(1, round(min(cell_width, cell_height) / 36))

    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            coordinate = f"{column_label(column + 1)}{row + 1}"
            left = round(column * cell_width)
            top = round(row * cell_height)
            right = round((column + 1) * cell_width)
            bottom = round((row + 1) * cell_height)

            draw.rectangle(
                (left, top, right, bottom),
                outline=line_color,
                width=line_width,
            )

            text_box = draw.textbbox((0, 0), coordinate, font=font)
            text_width = text_box[2] - text_box[0]
            text_height = text_box[3] - text_box[1]
            label_left = left + line_width + padding
            label_top = top + line_width + padding
            draw.rectangle(
                (
                    label_left,
                    label_top,
                    label_left + text_width + padding * 2,
                    label_top + text_height + padding * 2,
                ),
                fill=(0, 0, 0),
            )
            draw.text(
                (label_left + padding - text_box[0], label_top + padding - text_box[1]),
                coordinate,
                font=font,
                fill=(255, 255, 255),
            )

    return image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Screenshot the main display with a labeled 31x31 grid."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("milo-grid.png"),
        help="Where to save the image (default: milo-grid.png).",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the image after saving it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        image = capture_screen()
    except RuntimeError as error:
        print(f"Milo: {error}", file=sys.stderr)
        return 1

    draw_grid(image).save(output)
    print(f"Milo: saved {output}")

    if not args.no_open:
        subprocess.run(["open", str(output)], check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
