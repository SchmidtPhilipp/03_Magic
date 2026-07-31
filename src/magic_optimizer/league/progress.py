# src/magic_optimizer/league/progress.py
from __future__ import annotations

from dataclasses import asdict, dataclass

from magic_optimizer.league.store import League
from magic_optimizer.league.types import JobState
from magic_optimizer.match_oracle.health import forge_available


@dataclass
class JobProgress:
    challenges: int = 0
    best_deck_id: str | None = None
    best_winrate: float = 0.0
    games_vs_top: int = 0
    league_size: int = 0
    forge_available: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def snapshot_progress(
    state: JobState | None,
    league: League,
) -> JobProgress:
    state = state or JobState()
    return JobProgress(
        challenges=state.challenges,
        best_deck_id=state.best_deck_id,
        best_winrate=state.best_winrate,
        games_vs_top=state.games_vs_top,
        league_size=len(league),
        forge_available=bool(forge_available()),
    )
