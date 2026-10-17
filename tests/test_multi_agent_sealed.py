# tests/test_multi_agent_sealed.py
from pathlib import Path

from magic_optimizer.deck_picker.types import CardPool, DeckConstraints
from magic_optimizer.selfplay.multi_agent import MultiAgentSealedLoop
from magic_optimizer.selfplay.oracle_factory import make_oracle


def _factory(epoch: int, agent_id: int) -> CardPool:
    return CardPool({f"E{epoch}A{agent_id}C{i}": 4 for i in range(50)})


def test_train_refreshes_all_agent_pools_symmetrically():
    epochs_seen: list[tuple[int, int]] = []

    def factory(epoch: int, agent_id: int) -> CardPool:
        epochs_seen.append((epoch, agent_id))
        return _factory(epoch, agent_id)

    loop = MultiAgentSealedLoop(
        oracle=make_oracle(backend="stub", seed=0),
        pool_factory=factory,
        constraints=DeckConstraints(deck_size=60, non_basic_target=40),
        n_agents=3,
        decks_per_agent=1,
        games_per_match=5,
        refresh_games=10,
        seed=1,
        retrain_every=2,
        dim=24,
    )
    result = loop.run_train(max_games=25, matches_per_epoch_cap=10)
    assert result["phase"] == "train"
    assert result["n_agents"] == 3
    assert result["refresh_count"] >= 1
    # Every epoch should assign pools to all 3 agents (no fixed hero in train).
    agent_ids = {aid for _, aid in epochs_seen}
    assert agent_ids == {0, 1, 2}
    assert all(not a.fixed_pool for a in loop.agents)


def test_verify_locks_only_hero_pool():
    def factory(epoch: int, agent_id: int) -> CardPool:
        return _factory(epoch, agent_id)

    loop = MultiAgentSealedLoop(
        oracle=make_oracle(backend="stub", seed=0),
        pool_factory=factory,
        constraints=DeckConstraints(deck_size=60, non_basic_target=40),
        n_agents=3,
        decks_per_agent=1,
        games_per_match=5,
        refresh_games=10,
        seed=3,
        retrain_every=5,
        dim=24,
    )
    loop.run_train(max_games=15, matches_per_epoch_cap=6)
    hero = CardPool({f"Hero{i}": 4 for i in range(50)})
    verify = loop.run_verify(hero, max_games=15, matches_per_epoch_cap=6, hero_agent_id=0)
    assert verify["phase"] == "verify"
    assert verify["hero_pool_copies"] == sum(hero.available.values())
    assert verify["hero_games"] > 0
    assert loop.agents[0].fixed_pool is True
    assert loop.agents[1].fixed_pool is False
    assert loop.agents[2].fixed_pool is False


def test_checkpoint_resume_continues_games(tmp_path: Path):
    def factory(epoch: int, agent_id: int) -> CardPool:
        return _factory(epoch, agent_id)

    ckpt = tmp_path / "ckpt.json"
    loop = MultiAgentSealedLoop(
        oracle=make_oracle(backend="stub", seed=0),
        pool_factory=factory,
        constraints=DeckConstraints(deck_size=60, non_basic_target=40),
        n_agents=3,
        decks_per_agent=1,
        games_per_match=5,
        refresh_games=10,
        seed=9,
        dim=24,
    )
    loop.checkpoint_path = ckpt
    loop.run_train(additional_games=15, matches_per_epoch_cap=6)
    games_after = loop.total_games
    epoch_after = loop.epoch
    assert ckpt.exists()
    assert games_after >= 15

    loop2 = MultiAgentSealedLoop(
        oracle=make_oracle(backend="stub", seed=0),
        pool_factory=factory,
        constraints=DeckConstraints(deck_size=60, non_basic_target=40),
        n_agents=3,
        decks_per_agent=1,
        games_per_match=5,
        refresh_games=10,
        seed=9,
        dim=24,
    )
    loop2.load_checkpoint(ckpt)
    assert loop2.total_games == games_after
    assert loop2.epoch == epoch_after
    loop2.checkpoint_path = ckpt
    loop2.run_train(additional_games=10, matches_per_epoch_cap=6)
    assert loop2.total_games >= games_after + 10
