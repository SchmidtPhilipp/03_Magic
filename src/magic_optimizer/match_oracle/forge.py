from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.dck import to_dck
from magic_optimizer.match_oracle.forge_runner import run_forge_sim
from magic_optimizer.match_oracle.types import ForgePlayerAI, MatchResult


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
        self.work_dir = (
            work_dir
            if work_dir is not None
            else os.environ.get("FORGE_WORK_DIR", tempfile.gettempdir())
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

        deck_dir = Path(
            tempfile.mkdtemp(prefix="forge-match-", dir=self.work_dir)
        )
        (deck_dir / "a.dck").write_text(to_dck(deck_a, name="Deck A"), encoding="utf-8")
        (deck_dir / "b.dck").write_text(to_dck(deck_b, name="Deck B"), encoding="utf-8")

        try:
            return run_forge_sim(
                java=self.java,
                jar=self.jar,
                deck_dir=str(deck_dir),
                deck_a_name="a",
                deck_b_name="b",
                games=games,
                timeout_sec=self.timeout_sec,
            )
        finally:
            shutil.rmtree(deck_dir, ignore_errors=True)
