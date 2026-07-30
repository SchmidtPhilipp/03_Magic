from __future__ import annotations

from collections import Counter

from magic_optimizer.deck_picker.types import CardRef


def to_dck(deck: list[CardRef], *, name: str = "Deck") -> str:
    counts: Counter[str] = Counter()
    for card in deck:
        if card.name:
            counts[card.name] += 1

    lines = ["[metadata]", f"Name={name}", "[Main]"]
    for card_name in sorted(counts):
        lines.append(f"{counts[card_name]} {card_name}")

    return "\n".join(lines) + "\n"
