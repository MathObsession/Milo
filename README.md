# Milo

Milo V0.1.1 captures the main Mac display, draws a red 31×31 coordinate grid over the full screenshot, and can ask Gemini **3.1 Flash-Lite** to locate an icon by name. Gemini first returns a tight normalized bounding box around the icon. Milo maps it to the nearest cell, then zooms into a 7×7 area of the gridded screenshot so Gemini can read the printed labels and refine the answer. The result is a spreadsheet-style coordinate: `A1` through `AE31`.

## Setup

```sh
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Put your Gemini API key in `.env`:

```sh
GEMINI_API_KEY=your-api-key-here
```

You can also set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) in your environment. The `.env` file is excluded from git.

macOS requires Screen Recording permission for your terminal in **System Settings > Privacy & Security > Screen Recording**.

## Use

Capture the grid only:

```sh
python3 milo.py
```

Locate an icon and highlight its cell:

```sh
python3 milo.py "Safari icon"
```

Return machine-readable output:

```sh
python3 milo.py "Wi-Fi icon" --json --no-open
```

The image is saved to `milo-grid.png` and opened in Preview by default. When Gemini finds the target, Milo prints its coordinate and confidence, then outlines the matching cell in yellow.

Example result:

```json
{
  "target": "Safari icon",
  "model": "gemini-3.1-flash-lite",
  "found": true,
  "coordinate": "A6",
  "coarse_coordinate": "A6",
  "refined": true,
  "confidence": 0.9,
  "description": "Safari icon",
  "reasoning": "The Safari icon is located in the Dock...",
  "center": {
    "x": 0.0281,
    "y": 0.1861
  },
  "bounding_box": {
    "left": 0.0115,
    "top": 0.1611,
    "right": 0.0448,
    "bottom": 0.2111
  },
  "image": "/path/to/milo-grid.png"
}
```

## Notes

- The raw screenshot and a zoomed grid crop are sent to the Gemini API only when a target is provided.
- If the refinement pass fails, Milo falls back to the coordinate derived from the full-screen bounding box.
- The grid renderer uses only Pillow; Gemini requests use the Python standard library.
- The API client retries temporary `429`, `5xx`, and network failures up to three times.
- Run the tests with `python3 -m unittest discover -s tests`.
