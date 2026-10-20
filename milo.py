#!/usr/bin/env python3
"""Milo V0.1.1: screenshot the display, draw a coordinate grid, and locate icons."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

from gemini import MODEL, GeminiError, locate_icon
from rendering import draw_grid, draw_highlight

__version__ = "0.1.1"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture the main display with a 31x31 coordinate grid, optionally "
            "using Gemini to locate an icon."
        )
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Milo {__version__}",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help='Icon to locate, for example: "Safari icon".',
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("milo-grid.png"),
        help="Where to save the image (default: milo-grid.png).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the localization result as JSON.",
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

    location = None

    if args.target:
        if not args.json:
            print(f'Milo: asking {MODEL} to find "{args.target}"...')
        try:
            location = locate_icon(image, args.target)
        except GeminiError as error:
            print(f"Milo: {error}", file=sys.stderr)
            draw_grid(image).save(output)
            return 1

    image = draw_grid(image)
    if location is not None and location.found and location.coordinate:
        image = draw_highlight(image, location.coordinate)

    image.save(output)

    if args.json:
        result = {
            "target": args.target,
            "model": MODEL if args.target else None,
            "found": location.found if location else None,
            "coordinate": location.coordinate if location else None,
            "coarse_coordinate": location.coarse_coordinate if location else None,
            "refined": location.refined if location else None,
            "confidence": location.confidence if location else None,
            "description": location.description if location else None,
            "reasoning": location.reasoning if location else None,
            "center": (
                {
                    "x": location.center[0],
                    "y": location.center[1],
                }
                if location and location.center
                else None
            ),
            "bounding_box": (
                {
                    "left": location.bounding_box[0],
                    "top": location.bounding_box[1],
                    "right": location.bounding_box[2],
                    "bottom": location.bounding_box[3],
                }
                if location and location.bounding_box
                else None
            ),
            "image": str(output),
        }
        print(json.dumps(result, indent=2))
    elif location is not None:
        if location.found and location.coordinate:
            description = f" — {location.description}" if location.description else ""
            print(
                f"Milo: {location.coordinate}{description} "
                f"(confidence {location.confidence:.0%})"
            )
        else:
            print(f'Milo: could not find "{args.target}" in the screenshot.')
        print(f"Milo: saved {output}")
    else:
        print(f"Milo: saved {output}")

    if not args.no_open:
        subprocess.run(["open", str(output)], check=False)

    if location is not None and not location.found:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
