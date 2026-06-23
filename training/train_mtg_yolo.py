#!/usr/bin/env python3
"""Train YOLO11 MTG card detector on gpu-ml-01 via compute scheduler."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Train mtg_card YOLO model")
    parser.add_argument(
        "--config",
        default=os.environ.get("JOB_DIR", ".") + "/config.yaml",
        help="Training config YAML",
    )
    args = parser.parse_args()

    cfg_path = Path(args.config)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    from ultralytics import YOLO

    base = cfg.get("base_model", "yolo11n.pt")
    data_yaml = cfg["dataset_yaml"]
    epochs = int(cfg.get("epochs", 50))
    imgsz = int(cfg.get("imgsz", 640))
    project = Path(cfg.get("project", os.environ.get("RESULT_DIR", "runs/mtg-yolo")))
    name = cfg.get("name", datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))

    model = YOLO(base)
    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        project=str(project),
        name=name,
        exist_ok=True,
        device=cfg.get("device", 0),
    )

    best = Path(results.save_dir) / "weights" / "best.pt"
    archive_root = Path(cfg.get("archive_dir", "/mnt/nas/ml/runs/mtg-yolo"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archive_dir = archive_root / stamp
    archive_dir.mkdir(parents=True, exist_ok=True)
    if best.is_file():
        shutil.copy2(best, archive_dir / "best.pt")
        deploy_path = archive_root / "latest" / "best.pt"
        deploy_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best, deploy_path)

    manifest = {
        "best_pt": str(best),
        "archive": str(archive_dir),
        "metrics": getattr(results, "results_dict", {}),
    }
    out = Path(os.environ.get("RESULT_DIR", project / name))
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
