"""Image rendering helpers for Milo's coordinate grid."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from coordinates import GRID_SIZE, cell_bounds, column_label, parse_coordinate

FONT_PATH = "/System/Library/Fonts/SFNS.ttf"


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default(size=size)


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
            left, top, right, bottom = cell_bounds(
                image.size, column + 1, row + 1
            )

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
                (
                    label_left + padding - text_box[0],
                    label_top + padding - text_box[1],
                ),
                coordinate,
                font=font,
                fill=(255, 255, 255),
            )

    return image


def draw_highlight(image: Image.Image, coordinate: str) -> Image.Image:
    """Highlight the cell returned by the vision model."""
    parsed = parse_coordinate(coordinate)
    if parsed is None:
        return image

    bounds = cell_bounds(image.size, parsed[0], parsed[1])
    outline_width = max(3, round(min(image.size) / 350))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(bounds, fill=(255, 215, 0, 55))
    draw.rectangle(
        bounds,
        outline=(255, 215, 0, 255),
        width=outline_width,
    )
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
