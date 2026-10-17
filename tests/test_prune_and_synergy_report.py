# tests/test_prune_and_synergy_report.py
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_script():
    path = ROOT / "scripts" / "prune_and_synergy_report.py"
    spec = importlib.util.spec_from_file_location("prune_and_synergy_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_report_script_with_facts_json(tmp_path: Path, capsys):
    csv_path = tmp_path / "col.csv"
    csv_path.write_text(
        "amount,card_name\n4,Big\n4,Small\n4,Bolt\n",
        encoding="utf-8",
    )
    facts = {
        "Big": {
            "name": "Big",
            "cmc": 2,
            "type_line": "Creature — X",
            "colors": ["G"],
            "power": 3,
            "toughness": 3,
            "keywords": [],
        },
        "Small": {
            "name": "Small",
            "cmc": 2,
            "type_line": "Creature — X",
            "colors": ["G"],
            "power": 2,
            "toughness": 2,
            "keywords": [],
        },
        "Bolt": {
            "name": "Bolt",
            "cmc": 1,
            "type_line": "Instant",
            "colors": ["R"],
            "power": None,
            "toughness": None,
            "keywords": [],
        },
    }
    facts_path = tmp_path / "facts.json"
    facts_path.write_text(json.dumps(facts), encoding="utf-8")
    jsonl = tmp_path / "m.jsonl"
    jsonl.write_text(
        '{"deck_a":["Big","Bolt"],"deck_b":["Small"],"winrate_a":1.0}\n',
        encoding="utf-8",
    )

    script = _load_script()
    rc = script.main(
        [
            "--collection-csv",
            str(csv_path),
            "--facts-json",
            str(facts_path),
            "--synergy-jsonl",
            str(jsonl),
            "--top",
            "5",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "dropped_count" in out
    assert "Small" in out
    assert "top_edges" in out
