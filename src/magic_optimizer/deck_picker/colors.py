"""Color-identity helpers for hard deck color limits."""
from __future__ import annotations

from collections.abc import Callable
from typing import Iterable

from magic_optimizer.deck_picker.types import BASIC_LANDS, CardRef, DeckConstraints

_WUBRG = frozenset({"W", "U", "B", "R", "G"})
_BASIC_TO_COLOR = {
    "Plains": "W",
    "Island": "U",
    "Swamp": "B",
    "Mountain": "R",
    "Forest": "G",
}


def normalize_colors(colors: Iterable[str] | None) -> frozenset[str]:
    if not colors:
        return frozenset()
    out: set[str] = set()
    for c in colors:
        u = str(c).upper()
        if u in _WUBRG:
            out.add(u)
    return frozenset(out)


def color_identity_from_info(data: dict | None) -> frozenset[str]:
    if not data:
        return frozenset()
    raw = data.get("color_identity")
    if raw is None:
        raw = data.get("colors")
    return normalize_colors(raw)


def color_identity_of_name(
    name: str,
    *,
    card_info: Callable[[str], dict | None] | None = None,
) -> frozenset[str]:
    if name in BASIC_LANDS:
        return frozenset({_BASIC_TO_COLOR[name]}) if name in _BASIC_TO_COLOR else frozenset()
    if card_info is None:
        return frozenset()
    return color_identity_from_info(card_info(name))


def deck_color_identity(
    decklist: list[CardRef],
    *,
    card_info: Callable[[str], dict | None] | None = None,
) -> frozenset[str]:
    ci: set[str] = set()
    for card in decklist:
        if card.name in BASIC_LANDS:
            continue
        ci |= color_identity_of_name(card.name, card_info=card_info)
    return frozenset(ci)


def card_fits_color_constraints(
    name: str,
    decklist: list[CardRef],
    constraints: DeckConstraints,
    *,
    card_info: Callable[[str], dict | None] | None = None,
) -> bool:
    """Return True if adding ``name`` respects max_colors / allowed_colors.

    Basics always fit here (mana fill is separate). With ``card_info`` set and
    active color constraints, unresolved names fail closed (not treated as
    colorless) so Scryfall misses cannot sneak past max_colors.
    """
    if name in BASIC_LANDS:
        return True
    max_colors = constraints.max_colors
    allowed = constraints.allowed_colors
    if max_colors is None and allowed is None:
        return True

    if card_info is not None:
        info = card_info(name)
        if info is None:
            return False
        card_ci = color_identity_from_info(info)
    else:
        card_ci = frozenset()
        # Unknown identity — do not filter (tests / demo pools without Scryfall)
        return True

    if allowed is not None:
        return card_ci <= frozenset(allowed)

    assert max_colors is not None
    if max_colors <= 0:
        return not card_ci
    deck_ci = deck_color_identity(decklist, card_info=card_info)
    return len(deck_ci | card_ci) <= int(max_colors)
