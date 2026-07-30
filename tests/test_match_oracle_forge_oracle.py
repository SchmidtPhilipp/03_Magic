from __future__ import annotations

from pathlib import Path

import pytest

from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.forge import ForgeMatchOracle
from magic_optimizer.match_oracle.types import ForgePlayerAI, MatchResult


def test_forge_match_oracle_play(monkeypatch, tmp_path: Path):
    captured: dict = {}

    def fake_run_forge_sim(**kwargs):
        captured.update(kwargs)
        return MatchResult(
            wins_a=2,
            wins_b=1,
            games_played=3,
            void_games=0,
            engine="forge",
        )

    monkeypatch.setattr(
        "magic_optimizer.match_oracle.forge.run_forge_sim",
        fake_run_forge_sim,
    )

    jar = tmp_path / "forge.jar"
    jar.write_text("fake")
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    deck_a = [CardRef("Shock")] * 20 + [CardRef("Mountain")] * 40
    deck_b = [CardRef("Bolt")] * 20 + [CardRef("Island")] * 40

    oracle = ForgeMatchOracle(
        jar=str(jar),
        java="java11",
        work_dir=str(work_dir),
        timeout_sec=42.0,
    )
    result = oracle.play(deck_a, deck_b, games=3)

    assert result.wins_a == 2
    assert result.wins_b == 1
    assert result.games_played == 3
    assert captured["java"] == "java11"
    assert captured["jar"] == str(jar)
    assert captured["games"] == 3
    assert captured["timeout_sec"] == 42.0
    assert captured["deck_a_name"] == "a"
    assert captured["deck_b_name"] == "b"

    deck_dir = Path(captured["deck_dir"])
    assert deck_dir.is_dir()
    assert deck_dir.parent == work_dir
    assert (deck_dir / "a.dck").read_text().startswith("[metadata]")
    assert "Shock" in (deck_dir / "a.dck").read_text()
    assert (deck_dir / "b.dck").read_text().startswith("[metadata]")
    assert "Bolt" in (deck_dir / "b.dck").read_text()


def test_forge_match_oracle_default_player():
    oracle = ForgeMatchOracle(jar="/tmp/forge.jar")
    assert isinstance(oracle.player, ForgePlayerAI)


def test_forge_match_oracle_custom_player():
    class CustomPlayer:
        name = "custom"

    player = CustomPlayer()
    oracle = ForgeMatchOracle(jar="/tmp/forge.jar", player=player)
    assert oracle.player is player


def test_forge_match_oracle_reads_env(monkeypatch, tmp_path: Path):
    jar = tmp_path / "env.jar"
    jar.write_text("fake")
    work_dir = tmp_path / "env-work"
    work_dir.mkdir()

    monkeypatch.setenv("FORGE_JAR", str(jar))
    monkeypatch.setenv("FORGE_JAVA", "env-java")
    monkeypatch.setenv("FORGE_TIMEOUT_SEC", "99")
    monkeypatch.setenv("FORGE_WORK_DIR", str(work_dir))

    captured: dict = {}

    def fake_run_forge_sim(**kwargs):
        captured.update(kwargs)
        return MatchResult(
            wins_a=1,
            wins_b=0,
            games_played=1,
            engine="forge",
        )

    monkeypatch.setattr(
        "magic_optimizer.match_oracle.forge.run_forge_sim",
        fake_run_forge_sim,
    )

    oracle = ForgeMatchOracle()
    oracle.play([CardRef("Shock")], [CardRef("Bolt")], games=1)

    assert captured["java"] == "env-java"
    assert captured["jar"] == str(jar)
    assert captured["timeout_sec"] == 99.0
    assert Path(captured["deck_dir"]).parent == work_dir


def test_forge_match_oracle_missing_jar_raises():
    with pytest.raises(RuntimeError, match="FORGE_JAR not set"):
        ForgeMatchOracle()


def test_forge_match_oracle_default_timeout(monkeypatch, tmp_path: Path):
    jar = tmp_path / "forge.jar"
    jar.write_text("fake")
    monkeypatch.delenv("FORGE_TIMEOUT_SEC", raising=False)

    captured: dict = {}

    def fake_run_forge_sim(**kwargs):
        captured["timeout_sec"] = kwargs["timeout_sec"]
        return MatchResult(
            wins_a=0,
            wins_b=0,
            games_played=0,
            void_games=1,
            engine="forge",
        )

    monkeypatch.setattr(
        "magic_optimizer.match_oracle.forge.run_forge_sim",
        fake_run_forge_sim,
    )

    ForgeMatchOracle(jar=str(jar)).play([CardRef("Shock")], [CardRef("Bolt")], games=1)
    assert captured["timeout_sec"] == 300.0
