from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from magic_optimizer.match_oracle.types import MatchResult

_RESULT_LINE = re.compile(
    r"RESULT\s+wins_a=(\d+)\s+wins_b=(\d+)\s+games=(\d+)",
    re.IGNORECASE,
)
_MATCH_RESULT_LINE = re.compile(
    r"Match\s+Result:\s*Ai\(1\)[^:]*:\s*(\d+)\s+Ai\(2\)[^:]*:\s*(\d+)",
    re.IGNORECASE,
)
_SCORE_LINE = re.compile(r"(\d+)\s*[-–]\s*(\d+)")


class ForgeParseError(Exception):
    """Raised when Forge simulation output cannot be parsed."""


def parse_forge_sim_output(text: str) -> tuple[int, int, int]:
    # Prefer the last RESULT / Match Result line — multi-game sims print
    # running scores after each game.
    for line in reversed(text.splitlines()):
        match = _RESULT_LINE.search(line)
        if match:
            wins_a, wins_b, games = (int(match.group(i)) for i in range(1, 4))
            return wins_a, wins_b, games

    for line in reversed(text.splitlines()):
        match = _MATCH_RESULT_LINE.search(line)
        if match:
            wins_a = int(match.group(1))
            wins_b = int(match.group(2))
            return wins_a, wins_b, wins_a + wins_b

    for line in reversed(text.splitlines()):
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
    java_opts: list[str] | None = None,
) -> list[str]:
    # Forge needs decks registered under its constructed dir and referenced by name.
    opts = list(java_opts) if java_opts is not None else ["-Xmx2048m"]
    cmd = [java, *opts, "-jar", jar, "sim", "-d", deck_a, deck_b, "-n", str(games), "-q"]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def _deck_stem(deck_name: str) -> str:
    name = os.path.basename(deck_name)
    if name.endswith(".dck"):
        return name[: -len(".dck")]
    return name


def run_forge_sim(
    *,
    java: str,
    jar: str,
    deck_dir: str,
    deck_a_name: str,
    deck_b_name: str,
    games: int,
    timeout_sec: float,
    cwd: str | None = None,
) -> MatchResult:
    del deck_dir  # decks must already live in Forge constructed dir; names only
    cmd = build_forge_sim_command(
        java=java,
        jar=jar,
        deck_a=_deck_stem(deck_a_name),
        deck_b=_deck_stem(deck_b_name),
        games=games,
    )
    run_cwd = cwd or str(Path(jar).resolve().parent)

    try:
        proc = subprocess.run(
            cmd,
            timeout=timeout_sec,
            capture_output=True,
            text=True,
            cwd=run_cwd,
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
