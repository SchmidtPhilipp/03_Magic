# Scan fixtures

Synthetic binder/table photos built from Scryfall card art.

```bash
PYTHONPATH=src python scripts/build_scan_fixtures.py
```

- `single.jpg` — one card
- `binder_3x3.jpg` — 3×3 grid
- `cards/` — source normals

OCR naming requires `rapidocr-onnxruntime`; without it detections stay `Unbekannt` until you edit in the UI.

## Distortion robustness

Transforms are generated on the fly in `tests/test_scan_transform_robustness.py`
(mirror, rotate, skew, perspective). Typical OpenCV counts on `binder_3x3.jpg`:

| Transform | Detections |
|-----------|------------|
| baseline / mirror | 9 |
| rotate ±15–20°, skew, perspective | 8–9 |
| strong perspective | ~9 |

```bash
PYTHONPATH=src pytest tests/test_scan_transform_robustness.py -v
```
