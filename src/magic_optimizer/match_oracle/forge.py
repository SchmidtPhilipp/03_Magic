from __future__ import annotations

import os
import uuid
from pathlib import Path

from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.dck import to_dck
from magic_optimizer.match_oracle.forge_runner import run_forge_sim
from magic_optimizer.match_oracle.types import ForgePlayerAI, MatchResult


def default_forge_decks_dir() -> Path:
    env = os.environ.get("FORGE_DECKS_DIR")
    if env:
        return Path(env)
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "Forge"
        / "decks"
        / "constructed"
    )


class ForgeMatchOracle:
    def __init__(
        self,
        *,
        jar: str | None = None,
        java: str = "java",
        work_dir: str | None = None,
        timeout_sec: float | None = None,
        player: ForgePlayerAI | None = None,
    ) -> None:
        self.jar = jar if jar is not None else os.environ.get("FORGE_JAR")
        if not self.jar:
            raise RuntimeError("FORGE_JAR not set")

        self.java = java if java != "java" else os.environ.get("FORGE_JAVA", "java")
        # Forge 2.x only loads constructed decks from its user constructed dir
        # (or FORGE_DECKS_DIR). work_dir is kept for API compatibility / override.
        self.work_dir = (
            work_dir
            if work_dir is not None
            else os.environ.get("FORGE_WORK_DIR")
            or str(default_forge_decks_dir())
        )
        if timeout_sec is not None:
            try:
                self.timeout_sec = float(timeout_sec)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"invalid timeout_sec: {timeout_sec!r}"
                ) from exc
        else:
            env_timeout = os.environ.get("FORGE_TIMEOUT_SEC")
            if env_timeout:
                try:
                    self.timeout_sec = float(env_timeout)
                except ValueError as exc:
                    raise RuntimeError(
                        f"invalid FORGE_TIMEOUT_SEC: {env_timeout!r}"
                    ) from exc
            else:
                self.timeout_sec = 300.0
        self.player = player if player is not None else ForgePlayerAI()

    def play(
        self,
        deck_a: list[CardRef],
        deck_b: list[CardRef],
        *,
        games: int,
    ) -> MatchResult:
        if games < 1:
            raise ValueError("games must be at least 1")

        deck_dir = Path(self.work_dir)
        deck_dir.mkdir(parents=True, exist_ok=True)
        suffix = uuid.uuid4().hex[:10]
        name_a = f"mo_{suffix}_a"
        name_b = f"mo_{suffix}_b"
        path_a = deck_dir / f"{name_a}.dck"
        path_b = deck_dir / f"{name_b}.dck"
        path_a.write_text(to_dck(deck_a, name=name_a), encoding="utf-8")
        path_b.write_text(to_dck(deck_b, name=name_b), encoding="utf-8")

        try:
            return run_forge_sim(
                java=self.java,
                jar=self.jar,
                deck_dir=str(deck_dir),
                deck_a_name=name_a,
                deck_b_name=name_b,
                games=games,
                timeout_sec=self.timeout_sec,
                cwd=str(Path(self.jar).resolve().parent),
            )
        finally:
            path_a.unlink(missing_ok=True)
            path_b.unlink(missing_ok=True)
