# tests/test_deck_picker_checkpoint.py
import json
from pathlib import Path

from magic_optimizer.deck_picker.checkpoint import (
    DeckRLState,
    load_checkpoint,
    save_checkpoint,
)
from magic_optimizer.deck_picker.types import CardRef, DeckConstraints


def test_roundtrip_checkpoint(tmp_path: Path):
    state = DeckRLState(
        deck=[CardRef("Shock"), CardRef("Island")],
        pool={"Shock": 4, "Bolt": 2},
        constraints=DeckConstraints(banned=frozenset({"Cancel"}), pinned=("Shock",)),
        ratings={"Shock": 9.0, "Bolt": 8.0},
        iteration=3,
        trajectory=[
            {"action": "add", "card": "Shock", "score": 9.0, "index": 1, "alternatives": []}
        ],
        meta={"source": "test"},
    )
    path = tmp_path / "deck_rl.json"
    save_checkpoint(path, state)
    loaded = load_checkpoint(path)
    assert [c.name for c in loaded.deck] == ["Shock", "Island"]
    assert loaded.pool == {"Shock": 4, "Bolt": 2}
    assert loaded.constraints.banned == frozenset({"Cancel"})
    assert loaded.constraints.pinned == ("Shock",)
    assert loaded.ratings["Shock"] == 9.0
    assert loaded.iteration == 3
    assert loaded.trajectory[0]["card"] == "Shock"
    assert loaded.meta["source"] == "test"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 1
