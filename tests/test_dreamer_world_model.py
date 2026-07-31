# tests/test_dreamer_world_model.py
from magic_optimizer.dreamer.replay import ReplayBuffer, Transition
from magic_optimizer.dreamer.world_model import WorldModel


def test_untrained_predicts_half():
    model = WorldModel(dim=16, seed=0)
    assert abs(model.predict_winrate(["A"] * 60, ["B"] * 60) - 0.5) < 1e-9


def test_fit_learns_skewed_matchups():
    buf = ReplayBuffer()
    strong = ["Alpha"] * 60
    weak = ["Beta"] * 60
    for _ in range(40):
        buf.add(Transition(tuple(strong), tuple(weak), 0.9))
        buf.add(Transition(tuple(weak), tuple(strong), 0.1))
    model = WorldModel(dim=32, seed=1)
    stats = model.fit(buf, epochs=300, lr=0.1)
    assert stats["n"] == 80
    ab = model.predict_winrate(strong, weak)
    ba = model.predict_winrate(weak, strong)
    assert ab > ba
    assert ab > 0.6


def test_checkpoint_roundtrip():
    buf = ReplayBuffer()
    buf.add(Transition(("A",) * 10, ("B",) * 10, 0.8))
    model = WorldModel(dim=8, seed=2)
    model.fit(buf, epochs=50, lr=0.2)
    data = model.to_dict()
    restored = WorldModel.from_dict(data)
    assert abs(
        restored.predict_winrate(["A"] * 10, ["B"] * 10)
        - model.predict_winrate(["A"] * 10, ["B"] * 10)
    ) < 1e-9
