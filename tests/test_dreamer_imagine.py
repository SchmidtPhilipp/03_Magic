# tests/test_dreamer_imagine.py
from pathlib import Path

from magic_optimizer.dreamer.imagine import rank_decks, score_deck_vs_opponents
from magic_optimizer.dreamer.replay import ReplayBuffer, Transition
from magic_optimizer.dreamer.train import train_world_model_from_jsonl
from magic_optimizer.dreamer.world_model import WorldModel


def test_score_and_rank():
    strong = ["Good"] * 60
    weak = ["Bad"] * 60
    buf = ReplayBuffer()
    for _ in range(20):
        buf.add(Transition(tuple(strong), tuple(weak), 0.9))
        buf.add(Transition(tuple(weak), tuple(strong), 0.1))
    model = WorldModel(dim=24, seed=0)
    model.fit(buf)
    s_strong = score_deck_vs_opponents(model, strong, [weak])
    s_weak = score_deck_vs_opponents(model, weak, [weak])
    assert s_strong > s_weak
    ranked = rank_decks(model, [weak, strong], [weak])
    assert ranked[0][1] == strong


def test_train_from_jsonl(tmp_path: Path):
    path = tmp_path / "r.jsonl"
    lines = []
    for _ in range(15):
        lines.append(
            '{"deck_a":["Good"]*60,"deck_b":["Bad"]*60,"winrate_a":0.9}'.replace(
                '["Good"]*60', str(["Good"] * 60).replace("'", '"')
            ).replace('["Bad"]*60', str(["Bad"] * 60).replace("'", '"'))
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    model = train_world_model_from_jsonl(path, dim=16, seed=0)
    assert model.predict_winrate(["Good"] * 60, ["Bad"] * 60) > 0.5
