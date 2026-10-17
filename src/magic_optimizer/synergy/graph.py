# src/magic_optimizer/synergy/graph.py
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from magic_optimizer.deck_picker.types import BASIC_LANDS, CardRef


def _edge_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


class SynergyGraph:
    def __init__(self) -> None:
        self._weights: dict[tuple[str, str], float] = defaultdict(float)

    def add_deck(self, names: Iterable[str], *, weight: float) -> None:
        non_basics = sorted(
            {str(n) for n in names if str(n) not in BASIC_LANDS and str(n)}
        )
        if weight == 0.0:
            # Still allow zero weights for tests; skip work if empty
            pass
        for i, a in enumerate(non_basics):
            for b in non_basics[i + 1 :]:
                self._weights[_edge_key(a, b)] += float(weight)

    def score_pair(self, a: str, b: str) -> float:
        if a == b or a in BASIC_LANDS or b in BASIC_LANDS:
            return 0.0
        return float(self._weights.get(_edge_key(a, b), 0.0))

    def top_edges(self, n: int = 20) -> list[tuple[str, str, float]]:
        items = [(a, b, w) for (a, b), w in self._weights.items() if w > 0]
        items.sort(key=lambda t: (-t[2], t[0], t[1]))
        return items[: max(0, n)]

    def __len__(self) -> int:
        return len(self._weights)


def bonus_for_candidate(
    graph: SynergyGraph,
    decklist: list[CardRef] | list[str],
    candidate: str,
    *,
    scale: float = 1.0,
) -> float:
    """Mean edge weight between candidate and current non-basics."""
    names: list[str] = []
    for item in decklist:
        name = item.name if isinstance(item, CardRef) else str(item)
        if name not in BASIC_LANDS:
            names.append(name)
    if not names or candidate in BASIC_LANDS:
        return 0.0
    scores = [graph.score_pair(candidate, n) for n in names]
    if not scores:
        return 0.0
    return float(scale) * (sum(scores) / len(scores))
