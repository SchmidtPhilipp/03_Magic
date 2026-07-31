# tests/test_dreamer_policy.py
from magic_optimizer.deck_picker.types import CardPool, DeckConstraints
from magic_optimizer.dreamer.policy import DreamerNextCardPolicy
from magic_optimizer.dreamer.replay import ReplayBuffer, Transition
from magic_optimizer.dreamer.world_model import WorldModel


def test_policy_ranks_strong_card_higher():
    strong_deck = ["Good"] * 40 + ["Plains"] * 20
    weak_deck = ["Bad"] * 40 + ["Plains"] * 20
    buf = ReplayBuffer()
    for _ in range(30):
        buf.add(Transition(tuple(strong_deck), tuple(weak_deck), 0.95))
        buf.add(Transition(tuple(weak_deck), tuple(strong_deck), 0.05))
    model = WorldModel(dim=32, seed=0)
    model.fit(buf)

    pool = CardPool({"Good": 4, "Bad": 4, "Meh": 4})
    constraints = DeckConstraints(deck_size=60, non_basic_target=40, max_copies=4)
    policy = DreamerNextCardPolicy(model, opponents=[weak_deck])
    scored = policy.next_card(pool, [], constraints, k=5)
    names = [s.card.name for s in scored]
    assert "Good" in names
    assert scored[0].card.name == "Good"


def test_policy_fallback_without_opponents():
    model = WorldModel(dim=8, seed=0)
    pool = CardPool({"Shock": 4, "Bolt": 4})
    constraints = DeckConstraints()
    policy = DreamerNextCardPolicy(
        model, opponents=[], fallback_ratings={"Shock": 5.0, "Bolt": 1.0}
    )
    scored = policy.next_card(pool, [], constraints, k=2)
    assert scored[0].card.name == "Shock"
