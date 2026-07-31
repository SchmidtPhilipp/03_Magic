# Scan fixtures

Synthetic binder/table photos built from Scryfall card art.

```bash
PYTHONPATH=src python scripts/build_scan_fixtures.py
```

- `single.jpg` — one card
- `binder_3x3.jpg` — 3×3 grid
- `cards/` — source normals

OCR naming requires `rapidocr-onnxruntime`; without it detections stay `Unbekannt` until you edit in the UI.
