"""Grid coordinate helpers shared by Milo's renderer and vision client."""

from __future__ import annotations

import re

GRID_SIZE = 31


def column_label(index: int) -> str:
    """Convert a 1-based column index to A, B, ..., Z, AA, AB, ..."""
    label = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label


def parse_coordinate(value: str) -> tuple[int, int] | None:
    """Parse a coordinate such as A1 or AE31 into a 1-based (column, row)."""
    match = re.fullmatch(r"([A-Za-z]{1,2})0*([0-9]{1,2})", value.strip())
    if match is None:
        return None

    letters, row_text = match.groups()
    column = 0
    for letter in letters.upper():
        column = column * 26 + (ord(letter) - ord("A") + 1)
    row = int(row_text)

    if not (1 <= column <= GRID_SIZE and 1 <= row <= GRID_SIZE):
        return None
    return column, row


def coordinate_for_point(
    image_size: tuple[int, int], x: float, y: float
) -> tuple[int, int]:
    """Return the 1-based (column, row) containing a pixel point."""
    width, height = image_size
    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive.")
    if not (0 <= x <= width and 0 <= y <= height):
        raise ValueError("Point is outside the image.")

    column = min(GRID_SIZE, int((x / width) * GRID_SIZE) + 1)
    row = min(GRID_SIZE, int((y / height) * GRID_SIZE) + 1)
    return column, row


def cell_bounds(
    image_size: tuple[int, int], column: int, row: int
) -> tuple[int, int, int, int]:
    """Return the pixel bounds of a grid cell, matching the renderer's layout."""
    width, height = image_size
    cell_width = width / GRID_SIZE
    cell_height = height / GRID_SIZE
    left = round((column - 1) * cell_width)
    top = round((row - 1) * cell_height)
    right = round(column * cell_width)
    bottom = round(row * cell_height)
    return left, top, right, bottom
