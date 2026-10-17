"""Build synthetic scan photos from card images (tests / fixtures)."""

from __future__ import annotations

import time
from pathlib import Path

import requests
from PIL import Image

from magic_optimizer.vision.scryfall import lookup_card_name, scryfall_get

DEFAULT_FIXTURE_NAMES = [
    "Lightning Bolt",
    "Counterspell",
    "Dark Ritual",
    "Giant Growth",
    "Swords to Plowshares",
    "Birds of Paradise",
    "Sol Ring",
    "Brainstorm",
    "Llanowar Elves",
]


def build_card_grid(
    card_image_paths: list[Path],
    *,
    cols: int,
    rows: int,
    out_path: Path,
    gap: int = 8,
    background: tuple[int, int, int] = (24, 28, 32),
) -> Path:
    """
    Tile card images into a cols×rows grid JPEG.

    Uses the first cols*rows paths; pads with solid tiles if fewer images.
    """
    if cols < 1 or rows < 1:
        raise ValueError("cols and rows must be >= 1")
    needed = cols * rows
    paths = list(card_image_paths[:needed])
    while len(paths) < needed:
        paths.append(None)  # type: ignore[arg-type]

    sample = next((p for p in paths if p is not None), None)
    if sample is None:
        raise ValueError("at least one card image required")
    with Image.open(sample) as im:
        cw, ch = im.size

    width = cols * cw + (cols + 1) * gap
    height = rows * ch + (rows + 1) * gap
    canvas = Image.new("RGB", (width, height), background)

    for idx, path in enumerate(paths):
        r, c = divmod(idx, cols)
        x = gap + c * (cw + gap)
        y = gap + r * (ch + gap)
        if path is None:
            tile = Image.new("RGB", (cw, ch), (60, 60, 60))
        else:
            tile = Image.open(path).convert("RGB").resize((cw, ch))
        canvas.paste(tile, (x, y))
        if path is not None:
            tile.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="JPEG", quality=90)
    return out_path


def download_scryfall_normals(
    names: list[str],
    dest_dir: Path,
    *,
    pause_s: float = 0.12,
) -> list[Path]:
    """
    Download normal-size Scryfall art for each card name into dest_dir.

    Returns paths in the same order as names (skips failures).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, name in enumerate(names):
        try:
            resp = scryfall_get(
                "https://api.scryfall.com/cards/named",
                params={"fuzzy": name},
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            uris = data.get("image_uris") or {}
            if not uris and data.get("card_faces"):
                uris = data["card_faces"][0].get("image_uris") or {}
            url = uris.get("normal") or uris.get("large") or uris.get("small")
            if not url:
                continue
            img_resp = requests.get(
                url,
                headers={
                    "User-Agent": "MagicOptimizer/1.0 (philipp; collection-scan)",
                },
                timeout=30,
            )
            img_resp.raise_for_status()
            safe = "".join(ch if ch.isalnum() else "_" for ch in name)[:40]
            path = dest_dir / f"{i:02d}_{safe}.jpg"
            path.write_bytes(img_resp.content)
            paths.append(path)
        except requests.RequestException:
            continue
        time.sleep(pause_s)
    return paths


def apply_scan_transform(
    image_path: Path,
    kind: str,
    out_path: Path,
) -> Path:
    """
    Write a transformed copy of a scan photo for robustness tests.

    Supported kinds: identity, mirror_h, mirror_v, rotate_15, rotate_m20,
    rotate_25, skew, perspective, perspective_strong.
    """
    try:
        import cv2
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("opencv required for scan transforms") from exc

    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(image_path)
    h, w = img.shape[:2]
    border = (24, 28, 32)

    if kind == "identity":
        out = img
    elif kind == "mirror_h":
        out = cv2.flip(img, 1)
    elif kind == "mirror_v":
        out = cv2.flip(img, 0)
    elif kind == "rotate_15":
        m = cv2.getRotationMatrix2D((w / 2, h / 2), 15, 1.0)
        out = cv2.warpAffine(img, m, (w, h), borderValue=border)
    elif kind == "rotate_m20":
        m = cv2.getRotationMatrix2D((w / 2, h / 2), -20, 1.0)
        out = cv2.warpAffine(img, m, (w, h), borderValue=border)
    elif kind == "rotate_25":
        m = cv2.getRotationMatrix2D((w / 2, h / 2), 25, 1.0)
        out = cv2.warpAffine(img, m, (w, h), borderValue=border)
    elif kind == "skew":
        src = np.float32([[0, 0], [w - 1, 0], [0, h - 1]])
        dst = np.float32([[0, 0], [w - 1, int(0.08 * h)], [int(0.06 * w), h - 1]])
        m = cv2.getAffineTransform(src, dst)
        out = cv2.warpAffine(img, m, (w, h), borderValue=border)
    elif kind in ("perspective", "perspective_strong"):
        src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
        if kind == "perspective":
            dst = np.float32(
                [
                    [int(0.08 * w), int(0.05 * h)],
                    [int(0.95 * w), int(0.02 * h)],
                    [int(0.98 * w), int(0.92 * h)],
                    [int(0.05 * w), int(0.95 * h)],
                ]
            )
        else:
            dst = np.float32(
                [
                    [int(0.15 * w), int(0.1 * h)],
                    [int(0.9 * w), int(0.05 * h)],
                    [int(0.98 * w), int(0.88 * h)],
                    [int(0.02 * w), int(0.95 * h)],
                ]
            )
        m = cv2.getPerspectiveTransform(src, dst)
        out = cv2.warpPerspective(img, m, (w, h), borderValue=border)
    else:
        raise ValueError(f"unknown transform kind: {kind}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out_path), out):
        raise OSError(f"failed to write {out_path}")
    return out_path
