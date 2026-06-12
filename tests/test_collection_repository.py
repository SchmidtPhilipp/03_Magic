"""Tests for collection repository."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from magic_optimizer.collection.repository import CollectionRepository


@pytest.fixture
def repo():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "test.db")
        yield CollectionRepository(db_path)


def test_create_and_list_collections(repo):
    user_id = repo.ensure_user("philipp")
    c1 = repo.create_collection(user_id, "FF Box", "Final Fantasy cards")
    assert c1["name"] == "FF Box"
    assert c1["card_count"] == 0

    collections = repo.list_collections(user_id)
    assert len(collections) == 1
    assert collections[0]["name"] == "FF Box"


def test_add_and_remove_card(repo):
    user_id = repo.ensure_user("philipp")
    coll = repo.create_collection(user_id, "Draft Pool")
    cid = coll["id"]

    card = repo.add_card(
        cid, user_id, card_name="Lightning Bolt", set_code="LEA", amount=2
    )
    assert card is not None
    assert card["amount"] == 2

    cards = repo.list_cards(cid, user_id)
    assert len(cards) == 1

    repo.remove_card(card["id"], cid, user_id)
    assert repo.list_cards(cid, user_id) == []


def test_import_csv_and_export_dataframe(repo):
    user_id = repo.ensure_user("philipp")
    coll = repo.create_collection(user_id, "Import Test")
    cid = coll["id"]

    df = pd.DataFrame(
        [
            {"card_name": "Forest", "amount": 3, "set_code": "FIN"},
            {"card_name": "Island", "amount": 1, "set_code": "FIN"},
        ]
    )
    count = repo.import_csv(cid, user_id, df)
    assert count == 2

    sets = repo.distinct_sets(cid, user_id)
    assert sets == ["FIN"]

    out = repo.to_optimizer_dataframe(cid, user_id, set_codes=["FIN"])
    assert len(out) == 4  # 3 forests + 1 island
    assert "Name" in out.columns
