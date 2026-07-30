from magic_optimizer.deck_picker.types import CardRef
from magic_optimizer.match_oracle.types import ForgePlayerAI, MatchResult


def test_winrate_a():
    r = MatchResult(wins_a=3, wins_b=1, games_played=4, engine="stub")
    assert r.winrate_a == 0.75


def test_winrate_zero_games():
    r = MatchResult(wins_a=0, wins_b=0, games_played=0)
    assert r.winrate_a == 0.0


def test_forge_player_ai_name():
    assert ForgePlayerAI().name == "forge_ai"
