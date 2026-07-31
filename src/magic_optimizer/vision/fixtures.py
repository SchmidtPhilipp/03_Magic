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
