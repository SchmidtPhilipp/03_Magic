from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from magic_optimizer.match_oracle.forge_runner import (
    ForgeParseError,
    build_forge_sim_command,
    parse_forge_sim_output,
    run_forge_sim,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "forge_sim_quiet.txt"


def test_parse_fixture_file():
    text = FIXTURE_PATH.read_text()
    assert parse_forge_sim_output(text) == (3, 1, 4)


def test_parse_result_line():
    assert parse_forge_sim_output("RESULT wins_a=5 wins_b=2 games=7") == (5, 2, 7)


def test_parse_score_on_result_line():
    text = "Simulation complete\nFinal result: 3–1\n"
    assert parse_forge_sim_output(text) == (3, 1, 4)


def test_parse_score_on_wins_line():
    text = "Total wins 2-2 after 4 games\n"
    assert parse_forge_sim_output(text) == (2, 2, 4)


def test_parse_real_forge_match_result_line():
    text = (
        "Game Outcome: Ai(1)-oracle_a has won because all opponents have lost\n"
        "Match Result: Ai(1)-oracle_a: 1 Ai(2)-oracle_b: 0 \n"
        "Game Result: Game 1 ended in 1352 ms. Ai(1)-oracle_a has won!\n"
    )
    assert parse_forge_sim_output(text) == (1, 0, 1)


def test_parse_uses_last_match_result_for_multi_game():
    text = (
        "Match Result: Ai(1)-a: 1 Ai(2)-b: 0 \n"
        "Match Result: Ai(1)-a: 1 Ai(2)-b: 1 \n"
        "Match Result: Ai(1)-a: 2 Ai(2)-b: 1 \n"
    )
    assert parse_forge_sim_output(text) == (2, 1, 3)


def test_parse_raises_on_unparsable():
    with pytest.raises(ForgeParseError):
        parse_forge_sim_output("no useful output here")


def test_build_forge_sim_command():
    cmd = build_forge_sim_command(
        java="java",
        jar="/opt/forge.jar",
        deck_a="deck_a",
        deck_b="deck_b",
        games=10,
    )
    assert cmd == [
        "java",
        "-Xmx2048m",
        "-jar",
        "/opt/forge.jar",
        "sim",
        "-d",
        "deck_a",
        "deck_b",
        "-n",
        "10",
        "-q",
    ]


def test_build_forge_sim_command_extra_args():
    cmd = build_forge_sim_command(
        java="java",
        jar="forge.jar",
        deck_a="a.dck",
        deck_b="b.dck",
        games=1,
        extra_args=["--verbose"],
    )
    assert cmd[-2:] == ["-q", "--verbose"]


def test_run_forge_sim_success(monkeypatch):
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="RESULT wins_a=3 wins_b=1 games=4\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_forge_sim(
        java="java",
        jar="/forge.jar",
        deck_dir="/decks",
        deck_a_name="a",
        deck_b_name="b",
        games=4,
        timeout_sec=30.0,
    )

    assert result.wins_a == 3
    assert result.wins_b == 1
    assert result.games_played == 4
    assert result.void_games == 0
    assert result.engine == "forge"
    assert captured["cmd"] == build_forge_sim_command(
        java="java",
        jar="/forge.jar",
        deck_a="a",
        deck_b="b",
        games=4,
    )
    assert captured["kwargs"]["timeout"] == 30.0
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True


def test_run_forge_sim_timeout(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_forge_sim(
        java="java",
        jar="/forge.jar",
        deck_dir="/decks",
        deck_a_name="a",
        deck_b_name="b",
        games=5,
        timeout_sec=1.0,
    )

    assert result.wins_a == 0
    assert result.wins_b == 0
    assert result.games_played == 0
    assert result.void_games == 5
    assert result.engine == "forge"
    assert result.details == "timeout"


def test_run_forge_sim_nonzero_exit(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="Forge crashed badly",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_forge_sim(
        java="java",
        jar="/forge.jar",
        deck_dir="/decks",
        deck_a_name="a",
        deck_b_name="b",
        games=3,
        timeout_sec=10.0,
    )

    assert result.wins_a == 0
    assert result.wins_b == 0
    assert result.games_played == 0
    assert result.void_games == 3
    assert result.engine == "forge"
    assert result.details == "Forge crashed badly"
