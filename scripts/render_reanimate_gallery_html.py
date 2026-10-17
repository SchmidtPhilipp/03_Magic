#!/usr/bin/env python3
"""Render data/decks/reanimate_playgroup_cards.html — full graveyard/reanimate pool."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/decks/reanimate_playgroup_cards.html"
UA = {"User-Agent": "MagicOptimizer/1.0 (reanimate-gallery)"}

SETS = {
    "INR": "Innistrad Remastered",
    "DSK": "Duskmourn: House of Horror",
    "SOS": "Secrets of Strixhaven",
    "FDN": "Foundations",
    "BLB": "Bloomburrow",
    "FIN": "Final Fantasy",
    "LTR": "Lord of the Rings",
    "DFT": "Aetherdrift",
    "TDM": "Tarkir: Dragonstorm",
}

ORACLE_BITS = [
    'o:"creature card from your graveyard to the battlefield"',
    'o:"creature card from a graveyard onto the battlefield"',
    'o:"creature card from your graveyard onto the battlefield"',
    'o:"all creature cards from all graveyards onto the battlefield"',
    'o:"return target creature card from your graveyard to the battlefield"',
    'o:"return target creature card from your graveyard to your hand"',
    'o:"from your graveyard to the battlefield"',
    'o:"from your graveyard onto the battlefield"',
    'o:"cast from your graveyard"',
    'o:"cast from the graveyard"',
    'keyword:unearth',
    'keyword:flashback',
    'keyword:disturb',
    'keyword:escape',
    'keyword:undying',
    'keyword:persist',
    'o:"mill three"',
    'o:"mill two"',
    'o:"discard a card"',
    'o:"surveil"',
    'name:loot',
    'name:rummage',
    'name:reanim',
    'name:zombify',
    'name:unburial',
    'name:exhume',
    'name:unearth',
    'name:gravecrawler',
    'name:bloodghast',
    'name:macabre',
    'name:"raise dead"',
    'name:"rise from"',
]


def scryfall_search(q: str) -> list[dict]:
    url = "https://api.scryfall.com/cards/search?" + urllib.parse.urlencode(
        {"q": q, "unique": "cards"}
    )
    cards: list[dict] = []
    while url:
        raw = subprocess.check_output(
            ["curl", "-sS", "-A", UA["User-Agent"], url],
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(raw)
        if data.get("object") == "error":
            break
        cards.extend(data.get("data", []))
        url = data.get("next_page")
        if url:
            time.sleep(0.12)
    return cards


def oracle_text(card: dict) -> str:
    parts = [card.get("oracle_text") or ""]
    for face in card.get("card_faces") or []:
        parts.append(face.get("oracle_text") or "")
    return "\n".join(parts).lower()


def image_uri(card: dict) -> str | None:
    if card.get("image_uris"):
        return card["image_uris"].get("normal")
    faces = card.get("card_faces") or []
    if faces and faces[0].get("image_uris"):
        return faces[0]["image_uris"].get("normal")
    return None


def bucket(card: dict) -> str:
    t = oracle_text(card)
    kws = [k.lower() for k in (card.get("keywords") or [])]
    name = (card.get("name") or "").lower()
    if any(
        s in t
        for s in [
            "creature card from your graveyard to the battlefield",
            "creature card from a graveyard onto the battlefield",
            "creature card from your graveyard onto the battlefield",
            "all creature cards from all graveyards onto the battlefield",
        ]
    ):
        return "reanimate"
    if "unearth" in t or "unearth" in kws:
        return "unearth"
    if "flashback" in t or "flashback" in kws:
        return "flashback"
    if "disturb" in t or "disturb" in kws:
        return "disturb"
    if any(k in t or k in kws for k in ("undying", "persist", "escape")):
        return "recursive"
    if any(s in t for s in ("mill", "surveil", "discard")) or "loot" in name:
        return "enabler"
    if "graveyard" in t and ("return" in t or "cast" in t):
        return "graveyard"
    return "other"


ROLE_LABELS = {
    "all": "Alle Rollen",
    "reanimate": "Reanimate",
    "unearth": "Unearth",
    "flashback": "Flashback",
    "disturb": "Disturb",
    "recursive": "Recursive",
    "enabler": "Enabler",
    "graveyard": "GY-Synergy",
    "other": "Sonstiges",
}

RARITY_ORDER = {"common": 0, "uncommon": 1, "rare": 2, "mythic": 3}


def fetch_pool() -> list[dict]:
    seen: dict[str, dict] = {}
    for code in SETS:
        parts = [f"set:{code.lower()} ({bit})" for bit in ORACLE_BITS]
        for i in range(0, len(parts), 8):
            batch = " OR ".join(parts[i : i + 8])
            for card in scryfall_search(batch):
                seen[card["id"]] = card
            time.sleep(0.2)
    out = []
    for card in seen.values():
        set_code = (card.get("set") or "").upper()
        if set_code not in SETS:
            continue
        out.append(
            {
                "setCode": set_code,
                "setName": SETS[set_code],
                "name": card.get("name"),
                "mana": card.get("mana_cost") or "—",
                "cmc": card.get("cmc") or 0,
                "role": bucket(card),
                "rarity": card.get("rarity") or "unknown",
                "image": image_uri(card),
                "uri": card.get("scryfall_uri") or "#",
            }
        )
    out.sort(
        key=lambda c: (
            list(SETS).index(c["setCode"]) if c["setCode"] in SETS else 99,
            RARITY_ORDER.get(c["rarity"], 9),
            c["cmc"],
            c["name"],
        )
    )
    return out


HTML_TMPL = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Reanimate-Pool — Playgroup Sets</title>
<style>
  :root {{
    --bg:#12141a; --panel:#1a1d26; --text:#e8eaed; --muted:#9aa0a6;
    --accent:#8ab4f8; --border:#2a2f3a; --good:#81c995; --warn:#fdd663; --danger:#f28b82;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"IBM Plex Sans","Segoe UI",system-ui,sans-serif; background:var(--bg); color:var(--text); }}
  header {{ position:sticky; top:0; z-index:10; background:var(--panel); border-bottom:1px solid var(--border);
    padding:14px 16px; display:flex; flex-wrap:wrap; gap:10px; align-items:center; }}
  h1 {{ font-size:18px; font-weight:600; margin:0 12px 0 0; }}
  .stats {{ display:flex; gap:8px; flex-wrap:wrap; width:100%; }}
  .stat {{ background:var(--bg); border:1px solid var(--border); border-radius:8px; padding:6px 10px; font-size:12px; color:var(--muted); }}
  .stat strong {{ color:var(--text); font-size:14px; margin-right:4px; }}
  input[type=search] {{ flex:1; min-width:180px; max-width:360px; background:var(--bg); color:var(--text);
    border:1px solid var(--border); border-radius:6px; padding:8px 10px; font-size:14px; }}
  .filters, .sets, .rarity {{ display:flex; gap:6px; flex-wrap:wrap; width:100%; }}
  button.chip {{ background:transparent; color:var(--muted); border:1px solid var(--border);
    border-radius:999px; padding:6px 12px; cursor:pointer; font-size:13px; }}
  button.chip.active {{ color:var(--text); border-color:var(--accent); background:#243044; }}
  .meta {{ color:var(--muted); font-size:12px; width:100%; }}
  main {{ padding:16px; max-width:1500px; margin:0 auto; }}
  .set-block {{ margin-bottom:28px; }}
  .set-title {{ font-size:15px; font-weight:600; margin:0 0 12px; padding-bottom:8px;
    border-bottom:1px solid var(--border); color:var(--accent); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:12px; }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden;
    display:flex; flex-direction:column; }}
  .card:hover {{ border-color:var(--accent); }}
  .card img {{ width:100%; aspect-ratio:5/7; object-fit:cover; background:#0b0d11; display:block; }}
  .card .ph {{ width:100%; aspect-ratio:5/7; display:flex; align-items:center; justify-content:center;
    color:var(--muted); font-size:12px; padding:8px; text-align:center; }}
  .card .info {{ padding:10px; display:flex; flex-direction:column; gap:6px; }}
  .card .name {{ font-size:13px; font-weight:600; line-height:1.3; }}
  .card .mana {{ font-size:12px; color:var(--muted); font-family:monospace; }}
  .badges {{ display:flex; gap:4px; flex-wrap:wrap; }}
  .badge {{ font-size:10px; text-transform:uppercase; letter-spacing:.03em; padding:2px 6px;
    border-radius:4px; border:1px solid var(--border); color:var(--muted); }}
  .badge.r-common {{ color:#b0bec5; }}
  .badge.r-uncommon {{ color:#81c995; }}
  .badge.r-rare {{ color:#fdd663; }}
  .badge.r-mythic {{ color:#ff9f43; }}
  a.card-link {{ color:inherit; text-decoration:none; }}
  .empty {{ color:var(--muted); padding:32px 8px; text-align:center; }}
  footer {{ padding:16px; text-align:center; color:var(--muted); font-size:12px;
    border-top:1px solid var(--border); margin-top:24px; }}
</style>
</head>
<body>
<header>
  <h1>Reanimate-Pool — Playgroup Sets</h1>
  <div class="stats" id="stats"></div>
  <input type="search" id="q" placeholder="Karte suchen…" autocomplete="off" />
  <div class="filters" id="roleFilters"></div>
  <div class="rarity" id="rarityFilters"></div>
  <div class="sets" id="setFilters"></div>
  <div class="meta" id="meta"></div>
</header>
<main id="main"></main>
<footer>Vollständiger Graveyard/Reanimate-Pool · Scryfall · {total} Karten</footer>
<script>
const CARDS = {cards_json};
const SET_ORDER = {set_order_json};
const ROLE_LABELS = {role_labels_json};
const RARITY_LABELS = {{ all:"Alle", common:"Common", uncommon:"Uncommon", rare:"Rare", mythic:"Mythic" }};
let roleFilter = "all";
let setFilter = "all";
let rarityFilter = "all";

function countRole(r) {{ return r==="all" ? CARDS.length : CARDS.filter(c=>c.role===r).length; }}
function countRarity(r) {{ return r==="all" ? CARDS.length : CARDS.filter(c=>c.rarity===r).length; }}

function renderStats() {{
  const commons = CARDS.filter(c=>c.rarity==="common").length;
  const uncommons = CARDS.filter(c=>c.rarity==="uncommon").length;
  document.getElementById("stats").innerHTML = [
    ["Gesamt", CARDS.length], ["Common", commons], ["Uncommon", uncommons],
    ["Reanimate", countRole("reanimate")], ["Enabler", countRole("enabler")], ["Flashback", countRole("flashback")],
  ].map(([l,n])=>`<div class="stat"><strong>${{n}}</strong>${{l}}</div>`).join("");
}}

function chipRow(elId, items, active, onPick) {{
  const el = document.getElementById(elId); el.innerHTML = "";
  items.forEach(([id,label,count]) => {{
    const b = document.createElement("button");
    b.className = "chip" + (active===id ? " active" : "");
    b.textContent = count!=null ? `${{label}} (${{count}})` : label;
    b.onclick = () => onPick(id);
    el.appendChild(b);
  }});
}}

function renderFilters() {{
  chipRow("roleFilters", Object.entries(ROLE_LABELS).map(([id,label])=>[id,label,countRole(id)]), roleFilter, id=>{{roleFilter=id; render();}});
  chipRow("rarityFilters", Object.entries(RARITY_LABELS).map(([id,label])=>[id,label,countRarity(id)]), rarityFilter, id=>{{rarityFilter=id; render();}});
  const setItems = [["all","Alle Sets",null]].concat(SET_ORDER.map(code=>{{
    const n = CARDS.filter(c=>c.setCode===code).length;
    return [code, code, n];
  }}));
  chipRow("setFilters", setItems, setFilter, id=>{{setFilter=id; render();}});
}}

function filtered() {{
  const q = (document.getElementById("q").value||"").trim().toLowerCase();
  return CARDS.filter(c => {{
    if (roleFilter!=="all" && c.role!==roleFilter) return false;
    if (setFilter!=="all" && c.setCode!==setFilter) return false;
    if (rarityFilter!=="all" && c.rarity!==rarityFilter) return false;
    if (q && !c.name.toLowerCase().includes(q) && !c.setName.toLowerCase().includes(q)) return false;
    return true;
  }});
}}

function cardHtml(c) {{
  const img = c.image ? `<img src="${{c.image}}" alt="${{c.name}}" loading="lazy" />`
    : `<div class="ph">kein Bild</div>`;
  return `<a class="card-link" href="${{c.uri}}" target="_blank" rel="noopener">
    <article class="card">${{img}}<div class="info">
      <div class="name">${{c.name}}</div><div class="mana">${{c.mana}}</div>
      <div class="badges">
        <span class="badge">${{ROLE_LABELS[c.role]||c.role}}</span>
        <span class="badge r-${{c.rarity}}">${{c.rarity}}</span>
        <span class="badge">${{c.setCode}}</span>
      </div>
    </div></article></a>`;
}}

function render() {{
  renderStats(); renderFilters();
  const cards = filtered();
  const main = document.getElementById("main");
  if (!cards.length) {{
    main.innerHTML = '<div class="empty">Keine Karten für diesen Filter.</div>';
    document.getElementById("meta").textContent = "0 Karten";
    return;
  }}
  const groups = [];
  const order = setFilter==="all" ? SET_ORDER : [setFilter];
  order.forEach(code => {{
    const block = cards.filter(c=>c.setCode===code);
    if (block.length) groups.push({{code, name:block[0].setName, cards:block}});
  }});
  main.innerHTML = groups.map(g=>`
    <section class="set-block">
      <h2 class="set-title">${{g.name}} (${{g.code}}) — ${{g.cards.length}} Karten</h2>
      <div class="grid">${{g.cards.map(cardHtml).join("")}}</div>
    </section>`).join("");
  document.getElementById("meta").textContent = `${{cards.length}} Karten · Klick öffnet Scryfall`;
}}

document.getElementById("q").addEventListener("input", render);
render();
</script>
</body>
</html>
"""


def main() -> int:
    cards = fetch_pool()
    OUT.write_text(
        HTML_TMPL.format(
            total=len(cards),
            cards_json=json.dumps(cards, ensure_ascii=False),
            set_order_json=json.dumps(list(SETS.keys())),
            role_labels_json=json.dumps(ROLE_LABELS, ensure_ascii=False),
        ),
        encoding="utf-8",
    )
    by_rarity = defaultdict(int)
    for c in cards:
        by_rarity[c["rarity"]] += 1
    print(f"Wrote {OUT} ({len(cards)} cards)")
    print("by rarity:", dict(by_rarity))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
