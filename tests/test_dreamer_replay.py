# tests/test_dreamer_replay.py
from pathlib import Path

from magic_optimizer.dreamer.replay import ReplayBuffer, Transition


def test_add_and_len():
    buf = ReplayBuffer()
    buf.add(Transition(("A",), ("B",), 0.75))
    assert len(buf) == 1
    assert buf.as_list()[0].winrate_a == 0.75


def test_extend_from_records():
    buf = ReplayBuffer()
    n = buf.extend_from_records(
        [
            {"deck_a": ["Shock"], "deck_b": ["Bolt"], "winrate_a": 0.6},
            {"deck_a": ["X"], "deck_b": ["Y"], "wins_a": 3, "wins_b": 1, "games_played": 4},
        ]
    )
    assert n == 2
    assert abs(buf.as_list()[1].winrate_a - 0.75) < 1e-9


def test_load_jsonl(tmp_path: Path):
    path = tmp_path / "m.jsonl"
    path.write_text(
        '{"deck_a":["A"],"deck_b":["B"],"winrate_a":0.5}\n',
        encoding="utf-8",
    )
    buf = ReplayBuffer()
    assert buf.load_jsonl(path) == 1
