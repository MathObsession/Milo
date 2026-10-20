from __future__ import annotations

import json
import unittest

from PIL import Image

from gemini import GeminiError, _parse_location, _refine_crop


def parse(text: str, size: tuple[int, int]):
    return _parse_location(json.loads(text), size)


class LocationParsingTests(unittest.TestCase):
    def test_parses_valid_location(self) -> None:
        location = parse(
            json.dumps(
                {
                    "found": True,
                    "center_x": 0.5,
                    "center_y": 0.5,
                    "left": 0.48,
                    "top": 0.48,
                    "right": 0.52,
                    "bottom": 0.52,
                    "confidence": 0.82,
                    "description": "Test icon",
                    "reasoning": "Visible near the center.",
                }
            ),
            (320, 320),
        )
        self.assertTrue(location.found)
        self.assertEqual(location.coordinate, "P16")
        self.assertEqual(location.confidence, 0.82)
        self.assertEqual(location.bounding_box, (0.48, 0.48, 0.52, 0.52))

    def test_maps_bottom_right_to_ae31(self) -> None:
        location = parse(
            json.dumps(
                {
                    "found": True,
                    "center_x": 0.99,
                    "center_y": 0.99,
                    "left": 0.48,
                    "top": 0.48,
                    "right": 0.52,
                    "bottom": 0.52,
                    "confidence": 1,
                    "description": "Test icon",
                    "reasoning": "",
                }
            ),
            (320, 320),
        )
        self.assertEqual(location.coordinate, "AE31")

    def test_not_found_ignores_box(self) -> None:
        location = parse(
            json.dumps(
                {
                    "found": False,
                    "center_x": 0.1,
                    "center_y": 0.1,
                    "left": 0.1,
                    "top": 0.1,
                    "right": 0.2,
                    "bottom": 0.2,
                    "confidence": 0,
                    "description": "",
                    "reasoning": "",
                }
            ),
            (320, 320),
        )
        self.assertFalse(location.found)
        self.assertIsNone(location.coordinate)
        self.assertIsNone(location.bounding_box)

    def test_rejects_empty_box(self) -> None:
        with self.assertRaises(GeminiError):
            parse(
                json.dumps(
                    {
                        "found": True,
                        "left": 0.5,
                        "top": 0.5,
                        "right": 0.5,
                        "bottom": 0.6,
                        "confidence": 0.5,
                        "description": "",
                        "reasoning": "",
                    }
                ),
                (320, 320),
            )

    def test_refine_crop_stays_inside_grid(self) -> None:
        crop, first_column, first_row, last_column, last_row = _refine_crop(
            Image.new("RGB", (310, 310)), "A1"
        )
        self.assertEqual((first_column, first_row), (1, 1))
        self.assertEqual((last_column, last_row), (4, 4))
        self.assertEqual(crop.size, (80, 80))

    def test_rejects_unnormalized_box(self) -> None:
        with self.assertRaises(GeminiError):
            parse(
                json.dumps(
                    {
                        "found": True,
                        "left": 10,
                        "top": 10,
                        "right": 20,
                        "bottom": 20,
                        "confidence": 0.5,
                        "description": "",
                        "reasoning": "",
                    }
                ),
                (320, 320),
            )


if __name__ == "__main__":
    unittest.main()
