"""Normalize card images to the Scryfall reference size via center cover-crop."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

DEFAULT_WIDTH = 488
DEFAULT_HEIGHT = 680


def cover_crop_box(
    src_w: int,
    src_h: int,
    target_aspect: float,
) -> tuple[int, int, int, int]:
    """Return a centered cover-crop box ``(left, top, right, bottom)``.

    The crop keeps the full source on the limiting axis and trims the other
    so the result matches ``target_aspect`` (width / height).
    """
    if src_w <= 0 or src_h <= 0:
        raise ValueError(f"Invalid source size: {src_w}x{src_h}")
    if target_aspect <= 0:
        raise ValueError(f"Invalid target aspect: {target_aspect}")

    src_aspect = src_w / src_h
    if src_aspect > target_aspect:
        # Source too wide — crop left/right
        crop_h = src_h
        crop_w = int(round(crop_h * target_aspect))
        left = (src_w - crop_w) // 2
        top = 0
    else:
        # Source too tall (or equal) — crop top/bottom
        crop_w = src_w
        crop_h = int(round(crop_w / target_aspect))
        left = 0
        top = (src_h - crop_h) // 2

    right = left + crop_w
    bottom = top + crop_h
    # Clamp rounding drift
    left = max(0, left)
    top = max(0, top)
    right = min(src_w, right)
    bottom = min(src_h, bottom)
    return left, top, right, bottom


def normalize_image(
    source: Path | str,
    dest: Path | str,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> Path:
    """Center cover-crop to reference aspect, then resize exactly to ``width``×``height``.

    Never writes over ``source``. Creates parent directories for ``dest``.
    Uses Pillow LANCZOS resampling.
    """
    source = Path(source).resolve()
    dest = Path(dest).resolve()

    if not source.is_file():
        raise FileNotFoundError(f"Source image not found: {source}")
    if dest == source:
        raise ValueError(
            f"Refusing to overwrite original in place: {source}"
        )

    target_aspect = width / height
    with Image.open(source) as im:
        im = im.convert("RGB")
        box = cover_crop_box(im.width, im.height, target_aspect)
        cropped = im.crop(box)
        out = cropped.resize((width, height), Image.Resampling.LANCZOS)

    dest.parent.mkdir(parents=True, exist_ok=True)
    # Prefer JPEG for .jpg/.jpeg destinations; otherwise let Pillow infer
    suffix = dest.suffix.lower()
    save_kwargs: dict = {}
    if suffix in {".jpg", ".jpeg"}:
        save_kwargs["quality"] = 95
        save_kwargs["optimize"] = True
    out.save(dest, **save_kwargs)
    return dest
