# src/magic_optimizer/deck_picker/mana.py
"""Estimate color pips for basic-land filling."""

from __future__ import annotations

import re
from typing import Callable, Mapping

from magic_optimizer.deck_picker.types import BASIC_LANDS, CardRef

_WUBRG = ("W", "U", "B", "R", "G")
_PIP_RE = re.compile(r"\{([WUBRG])\}")
_HYBRID_RE = re.compile(r"\{([WUBRG])/([WUBRG])\}")


def pips_from_mana_cost(mana_cost: str | None) -> dict[str, int]:
    """Count colored pips in a Scryfall mana_cost string."""
    pips = {c: 0 for c in _WUBRG}
    if not mana_cost:
        return pips
    for color in _PIP_RE.findall(mana_cost):
        pips[color] += 1
    for a, b in _HYBRID_RE.findall(mana_cost):
        # Split hybrid weight: +1 to each side (conservative for land needs)
        pips[a] += 1
        pips[b] += 1
    return pips


def pips_from_color_identity(colors: list[str] | set[str] | None) -> dict[str, int]:
    pips = {c: 0 for c in _WUBRG}
    if not colors:
        return pips
    for c in colors:
        if c in pips:
            pips[c] += 1
    return pips


def merge_pips(*parts: Mapping[str, int]) -> dict[str, int]:
    out = {c: 0 for c in _WUBRG}
    for part in parts:
        for c in _WUBRG:
            out[c] += int(part.get(c, 0))
    return out


def estimate_deck_color_pips(
    decklist: list[CardRef],
    *,
    card_info: Callable[[str], dict | None] | None = None,
    color_hints: Mapping[str, Mapping[str, int]] | None = None,
) -> dict[str, int]:
    """
    Aggregate colored pips for non-basic cards.

    Prefer mana_cost pips from card_info (Scryfall-like dict); else color_identity;
    else optional color_hints[name] pip map.
    """
    total = {c: 0 for c in _WUBRG}
    for card in decklist:
        if card.name in BASIC_LANDS:
            continue
        if color_hints and card.name in color_hints:
            total = merge_pips(total, color_hints[card.name])
            continue
        if card_info is None:
            continue
        data = card_info(card.name) or {}
        cost = data.get("mana_cost")
        if not cost and "card_faces" in data:
            cost = "".join(
                face.get("mana_cost") or "" for face in data.get("card_faces") or []
            )
        from_cost = pips_from_mana_cost(cost)
        if sum(from_cost.values()) > 0:
            total = merge_pips(total, from_cost)
            continue
        identity = data.get("color_identity") or data.get("colors") or []
        total = merge_pips(total, pips_from_color_identity(identity))
    return total


def strip_basics(decklist: list[CardRef]) -> list[CardRef]:
    return [c for c in decklist if c.name not in BASIC_LANDS]
