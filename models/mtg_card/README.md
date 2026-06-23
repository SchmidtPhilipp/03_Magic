# MTG card YOLO weights

Place `best.pt` here after training or sync from NAS:

```bash
# From homelab repo (after train job completes):
./scripts/sync-mtg-yolo-model-to-magic.sh
```

Env override: `MTG_YOLO_MODEL=/path/to/best.pt`

Without weights, the app falls back to OpenCV contour detection.
