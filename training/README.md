# MTG YOLO training on gpu-ml-01

Fine-tune a single-class `mtg_card` detector via P-08 compute scheduler.

## Dataset (YOLO format)

On NAS (`/mnt/nas/ml/datasets/mtg-cards/`):

```
images/train/*.jpg
images/val/*.jpg
labels/train/*.txt   # class x_center y_center w h (normalized)
labels/val/*.txt
dataset.yaml         # copy from dataset.example.yaml
config.yaml          # copy from config.example.yaml
```

Reference weights: [JakeTurner616/mtg-card-segmentation-yolo11](https://huggingface.co/JakeTurner616/mtg-card-segmentation-yolo11)

## Submit training job

From **NetworkArchitecturePlan** repo (VPN, `COMPUTE_API_KEY` in `stacks/compute/.env`):

```bash
./scripts/submit-mtg-yolo-train.sh
```

Artifacts land in `/mnt/nas/ml/runs/mtg-yolo/<timestamp>/best.pt` and
`/mnt/nas/ml/runs/mtg-yolo/latest/best.pt`.

## Deploy weights to Magic CT

```bash
./scripts/sync-mtg-yolo-model-to-magic.sh
./scripts/deploy-magic.sh
```

Env on CT 167: `MTG_YOLO_MODEL=/opt/mtg-optimizer/models/mtg_card/best.pt`

Without weights the app uses OpenCV contour detection (Phase 1b fallback).
