from __future__ import annotations

import os
import re
import subprocess

from magic_optimizer.match_oracle.types import MatchResult

_RESULT_LINE = re.compile(
    r"RESULT\s+wins_a=(\d+)\s+wins_b=(\d+)\s+games=(\d+)",
    re.IGNORECASE,
)
_SCORE_LINE = re.compile(r"(\d+)\s*[-–]\s*(\d+)")


class ForgeParseError(Exception):
    """Raised when Forge simulation output cannot be parsed."""


def parse_forge_sim_output(text: str) -> tuple[int, int, int]:
    for line in text.splitlines():
        match = _RESULT_LINE.search(line)
        if match:
            wins_a, wins_b, games = (int(match.group(i)) for i in range(1, 4))
            return wins_a, wins_b, games

    for line in text.splitlines():
        lower = line.lower()
        if "result" not in lower and "wins" not in lower:
            continue
        match = _SCORE_LINE.search(line)
        if match:
            wins_a = int(match.group(1))
            wins_b = int(match.group(2))
            return wins_a, wins_b, wins_a + wins_b

    raise ForgeParseError("could not parse Forge simulation output")


def build_forge_sim_command(
    *,
    java: str,
    jar: str,
    deck_a: str,
    deck_b: str,
    games: int,
    extra_args: list[str] | None = None,
) -> list[str]:
    cmd = [
        java,
        "-jar",
        jar,
        "sim",
        "-d",
        deck_a,
        deck_b,
        "-n",
        str(games),
        "-q",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def _deck_path(deck_dir: str, deck_name: str) -> str:
    filename = deck_name if deck_name.endswith(".dck") else f"{deck_name}.dck"
    return os.path.join(deck_dir, filename)


def run_forge_sim(
    *,
    java: str,
    jar: str,
    deck_dir: str,
    deck_a_name: str,
    deck_b_name: str,
    games: int,
    timeout_sec: float,
) -> MatchResult:
    deck_a = _deck_path(deck_dir, deck_a_name)
    deck_b = _deck_path(deck_dir, deck_b_name)
    cmd = build_forge_sim_command(
        java=java,
        jar=jar,
        deck_a=deck_a,
        deck_b=deck_b,
        games=games,
    )

    try:
        proc = subprocess.run(
            cmd,
            timeout=timeout_sec,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return MatchResult(
            wins_a=0,
            wins_b=0,
            games_played=0,
            void_games=games,
            engine="forge",
            details="timeout",
        )

    if proc.returncode != 0:
        return MatchResult(
            wins_a=0,
            wins_b=0,
            games_played=0,
            void_games=games,
            engine="forge",
            details=(proc.stderr or "")[:500],
        )

    combined = (proc.stdout or "") + (proc.stderr or "")
    try:
        wins_a, wins_b, games_played = parse_forge_sim_output(combined)
    except ForgeParseError as exc:
        return MatchResult(
            wins_a=0,
            wins_b=0,
            games_played=0,
            void_games=games,
            engine="forge",
            details=str(exc)[:500],
        )

    return MatchResult(
        wins_a=wins_a,
        wins_b=wins_b,
        games_played=games_played,
        void_games=0,
        engine="forge",
    )
