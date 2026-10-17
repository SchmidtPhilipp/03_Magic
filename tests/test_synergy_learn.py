# tests/test_synergy_learn.py
from __future__ import annotations

from pathlib import Path

from magic_optimizer.synergy.learn import learn_synergy_from_jsonl


def test_learn_from_jsonl(tmp_path: Path):
    path = tmp_path / "m.jsonl"
    # deck_a wins fully with Shock+Bolt; deck_b has Opt alone
    path.write_text(
        "\n".join(
            [
                '{"deck_a":["Shock","Bolt","Mountain"],"deck_b":["Opt","Island"],"winrate_a":1.0}',
                '{"deck_a":["Shock","Bolt","Mountain"],"deck_b":["Opt","Island"],"winrate_a":0.8}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    g = learn_synergy_from_jsonl(path)
    assert g.score_pair("Shock", "Bolt") == 1.8  # 1.0 + 0.8 for side a
    # side b gets (1-winrate_a)
    assert g.score_pair("Opt", "Island") == 0.0  # Island is basic → no edge
    # Opt alone → no pairs
