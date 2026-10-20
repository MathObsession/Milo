"""Gemini-powered icon localization for Milo."""

from __future__ import annotations

import base64
import io
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image

from coordinates import (
    GRID_SIZE,
    cell_bounds,
    column_label,
    coordinate_for_point,
    parse_coordinate,
)
from prompts import (
    REFINE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_refine_prompt,
    build_user_prompt,
)
from rendering import draw_grid

MODEL = "gemini-3.1-flash-lite"
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent"
)
REQUEST_TIMEOUT_SECONDS = 120

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "found": {
            "type": "BOOLEAN",
            "description": "Whether the requested icon is visible in the screenshot.",
        },
        "center_x": {
            "type": "NUMBER",
            "description": "Normalized x coordinate of the icon's visual center.",
        },
        "center_y": {
            "type": "NUMBER",
            "description": "Normalized y coordinate of the icon's visual center.",
        },
        "left": {
            "type": "NUMBER",
            "description": "Normalized left edge of the icon box, from 0 to 1.",
        },
        "top": {
            "type": "NUMBER",
            "description": "Normalized top edge of the icon box, from 0 to 1.",
        },
        "right": {
            "type": "NUMBER",
            "description": "Normalized right edge of the icon box, from 0 to 1.",
        },
        "bottom": {
            "type": "NUMBER",
            "description": "Normalized bottom edge of the icon box, from 0 to 1.",
        },
        "confidence": {
            "type": "NUMBER",
            "description": "Confidence from 0 to 1 that the localization is correct.",
        },
        "description": {
            "type": "STRING",
            "description": "Short description of the icon that was matched.",
        },
        "reasoning": {
            "type": "STRING",
            "description": "Brief visual evidence supporting the localization.",
        },
    },
    "required": [
        "found",
        "center_x",
        "center_y",
        "left",
        "top",
        "right",
        "bottom",
        "confidence",
        "description",
        "reasoning",
    ],
}

COORDINATE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "found": {
            "type": "BOOLEAN",
            "description": "Whether the requested icon is visible in this crop.",
        },
        "coordinate": {
            "type": "STRING",
            "description": "The printed grid coordinate, such as A6 or AE31.",
        },
        "confidence": {
            "type": "NUMBER",
            "description": "Confidence from 0 to 1 in the coordinate.",
        },
        "description": {
            "type": "STRING",
            "description": "Short description of the icon that was matched.",
        },
    },
    "required": ["found", "coordinate", "confidence", "description"],
}


class GeminiError(RuntimeError):
    """Raised when Milo cannot complete a vision request."""


@dataclass(frozen=True)
class IconLocation:
    found: bool
    coordinate: str | None
    coarse_coordinate: str | None
    confidence: float
    description: str
    reasoning: str
    center: tuple[float, float] | None
    bounding_box: tuple[float, float, float, float] | None
    refined: bool


def load_api_key() -> str:
    """Load the Gemini key from the environment or the project's .env file."""
    for variable in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.environ.get(variable, "").strip()
        if value:
            return value

    env_path = Path(__file__).resolve().with_name(".env")
    if env_path.is_file():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}:
                value = value.strip().strip("\"'")
                if value:
                    return value

    raise GeminiError(
        "No Gemini API key found. Set GEMINI_API_KEY in your environment or "
        "add it to the .env file next to milo.py."
    )


def _image_data(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _generate(
    image: Image.Image,
    system_prompt: str,
    user_prompt: str,
    schema: dict,
    api_key: str,
    max_output_tokens: int,
) -> dict:
    body = json.dumps(
        {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": _image_data(image),
                            }
                        },
                        {"text": user_prompt},
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "mediaResolution": "MEDIA_RESOLUTION_HIGH",
                "thinkingConfig": {"thinkingLevel": "HIGH"},
            },
        }
    ).encode("utf-8")
    retryable_statuses = {429, 500, 502, 503, 504}

    for attempt in range(3):
        request = urllib.request.Request(
            API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=REQUEST_TIMEOUT_SECONDS
            ) as response:
                payload = json.load(response)
            return _json_payload(_response_text(payload))
        except urllib.error.HTTPError as error:
            raw_error = error.read().decode("utf-8", errors="replace")
            try:
                message = json.loads(raw_error).get(
                    "error", {}
                ).get("message", raw_error)
            except json.JSONDecodeError:
                message = raw_error

            if error.code in retryable_statuses and attempt < 2:
                time.sleep(2**attempt)
                continue
            raise GeminiError(
                f"Gemini API error ({error.code}): {message}"
            ) from error
        except urllib.error.URLError as error:
            if attempt < 2:
                time.sleep(2**attempt)
                continue
            raise GeminiError(f"Could not reach Gemini: {error.reason}") from error

    raise GeminiError("Gemini request failed after retrying.")


def _response_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        block_reason = (payload.get("promptFeedback") or {}).get("blockReason")
        detail = f" Prompt blocked: {block_reason}." if block_reason else ""
        raise GeminiError(f"Gemini returned no candidates.{detail}")

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    if finish_reason == "MAX_TOKENS":
        raise GeminiError("Gemini's response was truncated (MAX_TOKENS).")

    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part.get("text"), str) and not part.get("thought", False)
    ).strip()
    if not text:
        raise GeminiError(
            f"Gemini returned an empty response ({finish_reason or 'UNKNOWN'})."
        )
    return text


def _json_payload(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise GeminiError(f"Gemini returned invalid JSON: {error}") from error
    if not isinstance(data, dict):
        raise GeminiError("Gemini returned JSON that is not an object.")
    return data


def _parse_location(data: dict, image_size: tuple[int, int]) -> IconLocation:
    found = data.get("found")
    if not isinstance(found, bool):
        raise GeminiError("Gemini returned an invalid 'found' value.")

    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError) as error:
        raise GeminiError("Gemini returned an invalid confidence value.") from error
    confidence = min(1.0, max(0.0, confidence))

    description = str(data.get("description") or "").strip()
    reasoning = str(data.get("reasoning") or "").strip()

    if not found:
        return IconLocation(
            found=False,
            coordinate=None,
            coarse_coordinate=None,
            confidence=0.0,
            description=description,
            reasoning=reasoning,
            center=None,
            bounding_box=None,
            refined=False,
        )

    try:
        left = float(data["left"])
        top = float(data["top"])
        right = float(data["right"])
        bottom = float(data["bottom"])
        center_x = float(data.get("center_x", (left + right) / 2))
        center_y = float(data.get("center_y", (top + bottom) / 2))
    except (KeyError, TypeError, ValueError) as error:
        raise GeminiError("Gemini returned an invalid bounding box.") from error

    box = (left, top, right, bottom)
    center = (center_x, center_y)
    if not all(0 <= value <= 1 for value in box + center):
        raise GeminiError(
            "Gemini returned localization values outside normalized 0-1 coordinates."
        )
    if left >= right or top >= bottom:
        raise GeminiError("Gemini returned an empty bounding box.")

    width, height = image_size
    column, row = coordinate_for_point(
        image_size, center_x * width, center_y * height
    )
    coordinate = f"{column_label(column)}{row}"

    return IconLocation(
        found=True,
        coordinate=coordinate,
        coarse_coordinate=coordinate,
        confidence=confidence,
        description=description,
        reasoning=reasoning,
        center=center,
        bounding_box=box,
        refined=False,
    )


def _refine_crop(image: Image.Image, coordinate: str) -> tuple[Image.Image, int, int, int, int] | None:
    parsed = parse_coordinate(coordinate)
    if parsed is None:
        return None

    column, row = parsed
    margin = 3
    first_column = max(1, column - margin)
    first_row = max(1, row - margin)
    last_column = min(GRID_SIZE, column + margin)
    last_row = min(GRID_SIZE, row + margin)

    left, top, _, _ = cell_bounds((image.size), first_column, first_row)
    _, _, right, bottom = cell_bounds((image.size), last_column, last_row)
    crop = draw_grid(image.copy()).crop((left, top, right, bottom))
    crop = crop.resize(
        (crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS
    )
    return crop, first_column, first_row, last_column, last_row


def _refine_location(
    image: Image.Image, target: str, coarse_coordinate: str, api_key: str
) -> IconLocation | None:
    crop_result = _refine_crop(image, coarse_coordinate)
    if crop_result is None:
        return None

    crop, first_column, first_row, last_column, last_row = crop_result
    data = _generate(
        crop,
        REFINE_SYSTEM_PROMPT,
        build_refine_prompt(target),
        COORDINATE_SCHEMA,
        api_key,
        4096,
    )

    if data.get("found") is not True:
        return None

    parsed = parse_coordinate(str(data.get("coordinate") or ""))
    if parsed is None:
        return None
    column, row = parsed
    if not (first_column <= column <= last_column and first_row <= row <= last_row):
        return None

    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = min(1.0, max(0.0, confidence))

    return IconLocation(
        found=True,
        coordinate=f"{column_label(column)}{row}",
        coarse_coordinate=coarse_coordinate,
        confidence=confidence,
        description=str(data.get("description") or "").strip(),
        reasoning="",
        center=None,
        bounding_box=None,
        refined=True,
    )


def locate_icon(image: Image.Image, target: str) -> IconLocation:
    """Ask Gemini where the requested icon is and map it onto Milo's grid."""
    api_key = load_api_key()
    coarse = _parse_location(
        _generate(
            image,
            SYSTEM_PROMPT,
            build_user_prompt(target),
            RESPONSE_SCHEMA,
            api_key,
            8192,
        ),
        image.size,
    )
    if not coarse.found or coarse.coordinate is None:
        return coarse

    try:
        refined = _refine_location(
            image, target, coarse.coordinate, api_key
        )
    except GeminiError:
        return coarse
    if refined is None:
        return coarse

    refined = replace(
        refined,
        description=refined.description or coarse.description,
        reasoning=coarse.reasoning,
        center=coarse.center,
        bounding_box=coarse.bounding_box,
    )
    return refined
