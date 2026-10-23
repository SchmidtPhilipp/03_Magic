"""Proxy print pipeline: normalize alternate arts and prepare A4 print sheets."""

from magic_optimizer.proxy.config import ProxyConfig, load_config
from magic_optimizer.proxy.layout import (
    CardSlot,
    PageLayout,
    compute_layout,
    layout_from_config,
)
from magic_optimizer.proxy.manifest import (
    ManifestError,
    load_manifest,
    save_manifest,
    validate_manifest,
)
from magic_optimizer.proxy.normalize import normalize_image
from magic_optimizer.proxy.pdf import write_proxy_pdf
from magic_optimizer.proxy.validate import ValidationIssue, validate_proxy

__all__ = [
    "ProxyConfig",
    "load_config",
    "CardSlot",
    "PageLayout",
    "compute_layout",
    "layout_from_config",
    "ManifestError",
    "load_manifest",
    "save_manifest",
    "validate_manifest",
    "normalize_image",
    "write_proxy_pdf",
    "ValidationIssue",
    "validate_proxy",
]
