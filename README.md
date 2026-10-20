# Milo

V0.01 takes a screenshot of the main Mac display and overlays a red 31x31 grid covering the full screenshot. Each box is labeled in the top-left with spreadsheet-style coordinates (`A1` through `AE31`).

## Run

```sh
python3 -m pip install -r requirements.txt
python3 milo.py
```

The image is saved to `milo-grid.png` and opened in Preview.

If macOS blocks the screenshot, allow Screen Recording for your terminal in **System Settings > Privacy & Security > Screen Recording**.
