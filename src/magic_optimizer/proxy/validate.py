"""Validate proxy manifest entries against files and reference dimensions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, UnidentifiedImageError

from magic_optimizer.proxy.config import ProxyConfig
from magic_optimizer.proxy.manifest import validate_manifest

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding."""

    code: str
    message: str
    art_id: str | None = None
    path: str | None = None


def _resolve_art_path(
    entry: Mapping[str, Any],
    field: str,
    *,
    config: ProxyConfig | None,
    proxy_root: Path | None,
) -> Path | None:
    raw = entry.get(field)
    if raw is None or (isinstance(raw, str) and not str(raw).strip()):
        return None
    path = Path(str(raw))
    if path.is_absolute():
        return path
    base = proxy_root
    if base is None and config is not None:
        base = config.root
    if base is None:
        return path
    return (base / path).resolve()


def _check_image_file(
    path: Path,
    *,
    idx: int,
    field: str,
    art_id: str | None,
    ref_w: int,
    ref_h: int,
    check_dimensions: bool,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not path.is_file():
        issues.append(
            ValidationIssue(
                code="missing_file",
                message=f"arts[{idx}]: missing {field}: {path}",
                art_id=art_id,
                path=str(path),
            )
        )
        return issues

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        issues.append(
            ValidationIssue(
                code="unsupported_format",
                message=(
                    f"arts[{idx}]: unsupported format '{suffix}' "
                    f"for {field}: {path}"
                ),
                art_id=art_id,
                path=str(path),
            )
        )
        return issues

    if not check_dimensions:
        return issues

    try:
        with Image.open(path) as im:
            if im.size != (ref_w, ref_h):
                issues.append(
                    ValidationIssue(
                        code="wrong_dimensions",
                        message=(
                            f"arts[{idx}]: {field} is {im.size[0]}x{im.size[1]}, "
                            f"expected {ref_w}x{ref_h}: {path}"
                        ),
                        art_id=art_id,
                        path=str(path),
                    )
                )
    except UnidentifiedImageError:
        issues.append(
            ValidationIssue(
                code="unsupported_format",
                message=(
                    f"arts[{idx}]: cannot identify image for {field}: {path}"
                ),
                art_id=art_id,
                path=str(path),
            )
        )
    except OSError as exc:
        issues.append(
            ValidationIssue(
                code="missing_file",
                message=f"arts[{idx}]: cannot read {field}: {exc}",
                art_id=art_id,
                path=str(path),
            )
        )
    return issues


def validate_proxy(
    data: Mapping[str, Any],
    *,
    config: ProxyConfig | None = None,
    proxy_root: Path | str | None = None,
    check_normalized: bool = True,
) -> list[ValidationIssue]:
    """Check missing files, wrong dimensions, duplicate art_ids, unsupported formats."""
    issues: list[ValidationIssue] = []
    root = (
        Path(proxy_root).resolve()
        if proxy_root is not None
        else (config.root if config is not None else None)
    )
    ref_w = config.reference_width if config is not None else 488
    ref_h = config.reference_height if config is not None else 680

    for err in validate_manifest(data):
        if "duplicate art_id" in err:
            code = "duplicate_art_id"
        elif "missing required field" in err:
            code = "missing_field"
        else:
            code = "manifest"
        issues.append(ValidationIssue(code=code, message=err))

    arts: Sequence[Any] = data.get("arts") or []
    if not isinstance(arts, list):
        return issues

    for idx, entry in enumerate(arts):
        if not isinstance(entry, Mapping):
            continue
        art_id = entry.get("art_id")
        art_id_s = str(art_id) if art_id is not None else None

        source = _resolve_art_path(
            entry, "source_path", config=config, proxy_root=root
        )
        if source is not None:
            issues.extend(
                _check_image_file(
                    source,
                    idx=idx,
                    field="source_path",
                    art_id=art_id_s,
                    ref_w=ref_w,
                    ref_h=ref_h,
                    check_dimensions=False,
                )
            )

        if check_normalized and entry.get("normalized_path"):
            normalized = _resolve_art_path(
                entry, "normalized_path", config=config, proxy_root=root
            )
            if normalized is not None:
                issues.extend(
                    _check_image_file(
                        normalized,
                        idx=idx,
                        field="normalized_path",
                        art_id=art_id_s,
                        ref_w=ref_w,
                        ref_h=ref_h,
                        check_dimensions=True,
                    )
                )

        pw = entry.get("pixel_width")
        ph = entry.get("pixel_height")
        if pw is not None and ph is not None:
            if int(pw) != ref_w or int(ph) != ref_h:
                issues.append(
                    ValidationIssue(
                        code="wrong_dimensions",
                        message=(
                            f"arts[{idx}]: declared pixels {pw}x{ph}, "
                            f"expected {ref_w}x{ref_h}"
                        ),
                        art_id=art_id_s,
                    )
                )

    return issues
