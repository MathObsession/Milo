from __future__ import annotations

import unittest

from coordinates import (
    cell_bounds,
    column_label,
    coordinate_for_point,
    parse_coordinate,
)


class CoordinateTests(unittest.TestCase):
    def test_column_labels(self) -> None:
        self.assertEqual(column_label(1), "A")
        self.assertEqual(column_label(26), "Z")
        self.assertEqual(column_label(27), "AA")
        self.assertEqual(column_label(31), "AE")
        self.assertEqual(column_label(52), "AZ")
        self.assertEqual(column_label(53), "BA")

    def test_parse_coordinate(self) -> None:
        self.assertEqual(parse_coordinate("A1"), (1, 1))
        self.assertEqual(parse_coordinate("f18"), (6, 18))
        self.assertEqual(parse_coordinate("AE31"), (31, 31))
        self.assertIsNone(parse_coordinate("A0"))
        self.assertIsNone(parse_coordinate("AF1"))
        self.assertIsNone(parse_coordinate("A32"))
        self.assertIsNone(parse_coordinate("nope"))

    def test_cell_bounds_cover_image(self) -> None:
        size = (310, 310)
        self.assertEqual(cell_bounds(size, 1, 1), (0, 0, 10, 10))
        self.assertEqual(cell_bounds(size, 31, 31), (300, 300, 310, 310))

    def test_point_maps_to_coordinate(self) -> None:
        size = (310, 310)
        self.assertEqual(coordinate_for_point(size, 0, 0), (1, 1))
        self.assertEqual(coordinate_for_point(size, 155, 155), (16, 16))
        self.assertEqual(coordinate_for_point(size, 310, 310), (31, 31))

    def test_point_outside_image_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            coordinate_for_point((310, 310), -1, 0)


if __name__ == "__main__":
    unittest.main()
