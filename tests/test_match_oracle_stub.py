from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.stub import StubMatchOracle


def test_stub_deterministic_and_counts():
    a = [CardRef("Shock")] * 60
    b = [CardRef("Bolt")] * 60
    o = StubMatchOracle(seed=1)
    r1 = o.play(a, b, games=10)
    r2 = o.play(a, b, games=10)
    assert r1 == r2
    assert r1.games_played == 10
    assert r1.wins_a + r1.wins_b == 10
    assert r1.engine == "stub"


def test_stub_rejects_zero_games():
    o = StubMatchOracle()
    try:
        o.play([CardRef("Shock")], [CardRef("Bolt")], games=0)
        assert False
    except ValueError:
        pass
