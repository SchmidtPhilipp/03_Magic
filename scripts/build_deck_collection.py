#!/usr/bin/env python3
"""Build the active 3-deck collection + refresh no-trade / wishlist CSVs.

Each deck may use up to owned copies of every card independently
(no cross-deck exclusive allocation — sleeve one deck at a time).
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNION = ROOT / "data/collections/union/union_collection.csv"
OUT = ROOT / "data/decks/active"
KEEPERS = ROOT / "data/collections/keepers_no_trade.csv"
WISHLIST = ROOT / "data/collections/wishlist.csv"
BASIC_LANDS = frozenset({"Plains", "Island", "Swamp", "Mountain", "Forest"})


def load_inventory(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("card_name") or "").strip()
            if not name:
                continue
            counts[name] += max(1, int(float(row.get("amount") or 1)))
    return counts


def have(owned: Counter[str], name: str) -> int:
    return min(4, owned.get(name, 0))


def write_deck_txt(path: Path, counts: Counter[str]) -> None:
    lines = [
        f"{q} {n}"
        for n, q in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def take_upto(
    owned: Counter[str],
    into: Counter[str],
    name: str,
    qty: int,
    *,
    short: list[str],
) -> None:
    got = min(qty, have(owned, name))
    if got:
        into[name] += got
    if got < qty:
        short.append(f"{name} (want {qty}, own {have(owned, name)})")


def fill_basics(lands: Counter[str], pips: dict[str, int], total: int = 24) -> None:
    """Add basics proportional to pips until land count == total."""
    need = total - sum(lands.values())
    if need <= 0:
        return
    mapping = [("G", "Forest"), ("R", "Mountain"), ("U", "Island"), ("B", "Swamp"), ("W", "Plains")]
    active = [(c, b) for c, b in mapping if pips.get(c, 0) > 0]
    if not active:
        active = mapping
    weights = {b: max(1, pips.get(c, 0)) for c, b in active}
    basics = [b for _, b in active]
    total_w = sum(weights[b] for b in basics)
    raw = {b: need * weights[b] / total_w for b in basics}
    counts = {b: int(raw[b]) for b in basics}
    rem = need - sum(counts.values())
    for b in sorted(basics, key=lambda x: raw[x] - counts[x], reverse=True)[:rem]:
        counts[b] += 1
    for b, q in counts.items():
        if q:
            lands[b] += q


def build_deck(
    owned: Counter[str],
    *,
    label: str,
    spells: list[tuple[str, int]],
    land_picks: list[tuple[str, int]],
    pips: dict[str, int],
    pad: list[str],
    cut_priority: list[str] | None = None,
) -> dict:
    """Build one 60 with independent ownership caps (no global remaining)."""
    short: list[str] = []
    nb: Counter[str] = Counter()
    for name, qty in spells:
        take_upto(owned, nb, name, qty, short=short)

    for name in pad:
        while sum(nb.values()) < 36 and nb[name] < have(owned, name):
            nb[name] += 1
        if sum(nb.values()) >= 36:
            break

    cuts = list(cut_priority or []) + list(reversed(pad))
    for name in cuts:
        while sum(nb.values()) > 36 and nb.get(name, 0) > 0:
            nb[name] -= 1
            if nb[name] <= 0:
                del nb[name]
        if sum(nb.values()) <= 36:
            break
    # last resort: cut highest-cmc-looking leftovers alphabetically from 1-ofs not in first half of spells
    core = {n for n, _ in spells[:20]}
    if sum(nb.values()) > 36:
        for name in sorted(nb.keys()):
            if name in core:
                continue
            while sum(nb.values()) > 36 and nb.get(name, 0) > 0:
                nb[name] -= 1
                if nb[name] <= 0:
                    del nb[name]
            if sum(nb.values()) <= 36:
                break

    if sum(nb.values()) != 36:
        raise SystemExit(
            f"{label}: expected 36 nonlands, got {sum(nb.values())}; short={short}; have={dict(nb)}"
        )

    lands: Counter[str] = Counter()
    for name, qty in land_picks:
        if qty <= 0:
            continue
        take_upto(owned, lands, name, qty, short=short)
    fill_basics(lands, pips, total=24)
    # if still under 24 (too many land picks failed), add more basics
    while sum(lands.values()) < 24:
        # dump into highest pip basic
        best = max(
            [("G", "Forest"), ("R", "Mountain"), ("U", "Island"), ("B", "Swamp"), ("W", "Plains")],
            key=lambda x: pips.get(x[0], 0),
        )[1]
        lands[best] += 1
    while sum(lands.values()) > 24:
        # remove a basic first
        removed = False
        for b in ("Plains", "Swamp", "Island", "Mountain", "Forest"):
            if lands.get(b, 0) > 0:
                lands[b] -= 1
                if lands[b] <= 0:
                    del lands[b]
                removed = True
                break
        if not removed:
            # remove a nonbasic
            for n in list(lands):
                if n not in BASIC_LANDS:
                    lands[n] -= 1
                    if lands[n] <= 0:
                        del lands[n]
                    break

    final = nb + lands
    assert sum(final.values()) == 60, sum(final.values())
    return {
        "label": label,
        "shortfalls_vs_ideal": short,
        "deck": [
            {"qty": q, "name": n}
            for n, q in sorted(final.items(), key=lambda x: (-x[1], x[0]))
        ],
        "cards": list(final.elements()),
    }


def main() -> int:
    owned = load_inventory(UNION)

    decks = [
        build_deck(
            owned,
            label="Temur Ureni Dragons",
            spells=[
                ("Ureni, the Song Unending", 1),
                ("Niv-Mizzet, Parun", 1),
                ("Niv-Mizzet, the Firemind", 2),
                ("Hellkite Punisher", 1),
                ("Karakyk Guardian", 2),
                ("Boulderborn Dragon", 1),
                ("Nebula Dragon", 1),
                ("Breaching Dragonstorm", 1),
                ("Dragonback Assault", 1),
                ("Encroaching Dragonstorm", 1),
                ("Molten Exhale", 2),
                ("Dispelling Exhale", 1),
                ("Bathe in Dragonfire", 1),
                ("Bogardan Dragonheart", 1),
                ("Dragonsguard Elite", 1),
                ("Dragonstorm Globe", 1),
                ("Llanowar Elves", 4),
                ("Grow from the Ashes", 2),
                ("Primeval Titan", 1),
                ("Craterhoof Behemoth", 1),
                ("Lightning Bolt", 2),
                ("Burst Lightning", 1),
                ("Abrade", 1),
                ("Counterspell", 1),
                ("Consider", 1),
                ("Stock Up", 3),
                ("Bushwhack", 1),
                ("Snakeskin Veil", 1),
                ("Magda, the Hoardmaster", 1),
            ],
            land_picks=[
                ("Stomping Ground", 1),
                ("Thundering Falls", 1),
                ("Willowrush Verge", 1),
                ("Mistrise Village", 1),
                ("Swiftwater Cliffs", 2),
                ("Thornwood Falls", 2),
                ("Rugged Highlands", 2),
                ("Izzet Guildgate", 1),
                ("Gongaga, Reactor Town", 1),
                ("Lakeside Shack", 1),
                ("Spectacle Summit", 1),
                ("Evolving Wilds", 2),
                ("Unclaimed Territory", 1),  # name Dragon
                ("Secluded Courtyard", 1),
                ("Snow-Covered Island", 1),
                ("Snow-Covered Mountain", 1),
            ],
            pips={"G": 18, "R": 14, "U": 12},
            pad=[
                "Wild Hypothesis",
                "Giant Growth",
                "Heritage Reclamation",
                "Chocobo Kick",
                "Thrill of Possibility",
            ],
            cut_priority=[
                "Bogardan Dragonheart",
                "Dragonsguard Elite",
                "Dragonstorm Globe",
                "Bathe in Dragonfire",
                "Wild Hypothesis",
            ],
        ),
        build_deck(
            owned,
            label="Mardu Prison Reanimator",
            spells=[
                # win + reanimate package
                ("Griselbrand", 1),
                ("Laboratory Maniac", 2),
                ("Valgavoth's Faithful", 1),
                ("Crawl from the Cellar", 4),
                ("Evil Reawakened", 1),
                ("Macabre Waltz", 2),
                ("Vampire Soulcaller", 1),
                ("Macabre Reconstruction", 1),
                ("Troll of Khazad-dûm", 1),
                ("Gurmag Angler", 2),
                ("Subjugator Angel", 1),
                ("Doomsday Excruciator", 1),
                # stall / white
                ("Ghostly Prison", 1),
                ("Moment of Reckoning", 1),
                # dig / discard / yard
                ("Faithless Looting", 2),
                ("Reforge the Soul", 1),
                ("Resentful Revelation", 2),
                ("Ransack the Lab", 1),
                ("Village Rites", 2),
                ("Thrill of Possibility", 1),
                # removal
                ("Bitter Triumph", 1),
                ("Fell", 3),
                ("Lightning Bolt", 2),
                ("Flame Slash", 1),
            ],
            land_picks=[
                ("Blood Crypt", 1),
                ("Sacred Foundry", 1),
                ("Raucous Theater", 1),
                ("Bloodfell Caves", 1),
                ("Windswept Heath", 1),
                ("Evolving Wilds", 2),
                ("Escape Tunnel", 1),
                ("Terramorphic Expanse", 1),
                ("Snow-Covered Plains", 1),
                ("Snow-Covered Swamp", 1),
                ("Snow-Covered Mountain", 1),
            ],
            pips={"B": 16, "R": 10, "W": 8},
            pad=[
                "Lie in Wait",
                "Deadly Allure",
                "Stargaze",
                "Necrotic Wound",
                "Soul-Shackled Zombie",
                "Siege Zombie",
                "Elder Brain",
            ],
            cut_priority=[
                "Soul-Shackled Zombie",
                "Siege Zombie",
                "Necrotic Wound",
                "Stargaze",
                "Deadly Allure",
                "Lie in Wait",
                "Elder Brain",
            ],
        ),
        build_deck(
            owned,
            label="UR Stock Up Tempo",
            spells=[
                ("Niv-Mizzet, Parun", 1),
                ("Niv-Mizzet, the Firemind", 2),
                ("Stock Up", 3),
                ("Ponder", 1),
                ("Chandra, Heart of Fire", 1),
                ("Ral Zarek", 1),
                ("Valley Floodcaller", 1),
                ("Emberheart Challenger", 1),
                ("Heartfire Hero", 1),
                ("Goblin Electromancer", 1),
                ("Lightning Bolt", 2),
                ("Counterspell", 1),
                ("Consider", 1),
                ("Into the Roil", 1),
                ("Abrade", 1),
                ("Past in Flames", 1),
                ("Thrill of Possibility", 1),
                ("Thunder Magic", 1),
                ("Unending Whisper", 1),
                ("Syncopate", 2),
                ("Quicken", 1),
                ("Stream of Thought", 1),
                ("Fractalize", 1),
                ("Essence Flux", 1),
                ("Lamplight Phoenix", 1),
                ("Barret Wallace", 1),
                ("Fearless Swashbuckler", 1),
                ("Relentless X-ATM092", 1),
                ("Burning Sun's Avatar", 1),
                ("Strangle", 1),
                ("Ranger's Firebrand", 1),
                ("Full Bore", 1),
                ("Felonious Rage", 1),
            ],
            land_picks=[
                ("Thundering Falls", 1),
                ("Swiftwater Cliffs", 3),
                ("Spectacle Summit", 2),
                ("Izzet Guildgate", 1),
                ("Wandering Fumarole", 1),
                ("Mistrise Village", 1),
                ("Evolving Wilds", 2),
                ("Snow-Covered Island", 1),
                ("Snow-Covered Mountain", 1),
                ("Rivendell", 1),
            ],
            pips={"U": 16, "R": 14},
            pad=[
                "Might of the Meek",
                "Duel Tactics",
                "String of Disappearances",
                "Magic Damper",
                "Downsize",
                "Gearseeker Serpent",
            ],
        ),
    ]

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("0*.txt"):
        old.unlink()

    report_decks = []
    for i, d in enumerate(decks, 1):
        slug = d["label"].lower().replace(" ", "_").replace("/", "_")
        path = OUT / f"{i:02d}_{slug}.txt"
        write_deck_txt(path, Counter(d["cards"]))
        report_decks.append(
            {
                "label": d["label"],
                "file": str(path.relative_to(ROOT)),
                "shortfalls_vs_ideal": d["shortfalls_vs_ideal"],
                "stock_up": Counter(d["cards"]).get("Stock Up", 0),
            }
        )
        c = Counter(d["cards"])
        basics = sum(c[b] for b in BASIC_LANDS)
        print(
            f"{d['label']}: size={sum(c.values())} "
            f"Stock Up x{c.get('Stock Up', 0)} Bolts x{c.get('Lightning Bolt', 0)} "
            f"basics={basics} shortfalls={len(d['shortfalls_vs_ideal'])}"
        )

    # keepers / wishlist unchanged content — rewrite confirmed keepers + wishlist
    # (reuse previous lists from file if present; else seed)
    # Keep existing keepers/wishlist files; only update README + report.

    report = {
        "inventory": str(UNION.relative_to(ROOT)),
        "allocation_rule": "Each deck may use up to owned copies independently (no exclusive share).",
        "decks": report_decks,
        "keepers_file": "data/collections/keepers_no_trade.csv",
        "wishlist_file": "data/collections/wishlist.csv",
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "README.txt").write_text(
        "\n".join(
            [
                "Active deck collection",
                "Rule: each deck can use every card up to owned qty (sleeve one deck at a time).",
                "",
                *[f"  - {d['file']}  (Stock Up x{d['stock_up']})" for d in report_decks],
                "",
                "Find cards with images: data/decks/active/find_cards.html",
                "Rebuild: PYTHONPATH=src python3 scripts/build_deck_collection.py",
                "Refresh images (+ verified top-N): PYTHONPATH=src python3 scripts/render_deck_find_html.py --top-n 5",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(report_decks, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
