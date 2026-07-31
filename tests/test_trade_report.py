# tests/test_trade_report.py
from magic_optimizer.deck_picker.trade import trade_report
from magic_optimizer.deck_picker.types import CardPool, CardRef


def test_trade_report_missing_and_present():
    deck = [CardRef("Shock")] * 4 + [CardRef("Bolt")] * 2 + [CardRef("Plains")] * 10
    owned = CardPool({"Shock": 2, "Bolt": 2, "Island": 20})
    report = trade_report(deck, owned)
    missing = {n: q for n, q in report["missing"]}
    assert missing["Shock"] == 2
    assert "Bolt" not in missing
    assert "Plains" not in missing
    assert report["missing_total"] == 2
    present = {n: q for n, q in report["present"]}
    assert present["Bolt"] == 2
    assert present["Shock"] == 2


def test_trade_report_accepts_string_names():
    report = trade_report(["Shock", "Shock"], CardPool({"Shock": 0}))
    assert report["missing"] == [["Shock", 2]]
