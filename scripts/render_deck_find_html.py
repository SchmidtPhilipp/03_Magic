#!/usr/bin/env python3
"""Render data/decks/active/find_cards.html with Scryfall card images.

Includes active decks plus verified top-N decks as a separate section tab.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_DIR = ROOT / "data/decks/active"
VERIFIED_DIR = ROOT / "data/decks/verified"
OUT_HTML = ACTIVE_DIR / "find_cards.html"
CACHE = ROOT / "runs/scryfall_images_cache.json"
UA = {
    "User-Agent": "MagicOptimizer/1.0 (philipp; deck-find-images)",
    "Accept": "application/json",
}
BASICS = frozenset({"Plains", "Island", "Swamp", "Mountain", "Forest"})
LINE_RE = re.compile(r"^(\d+)\s+(.+)$")


def parse_deck(path: Path) -> Counter[str]:
    c: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        c[m.group(2).strip()] += int(m.group(1))
    return c


def _is_image_entry(value: object) -> bool:
    """True for a usable image-cache hit (URL present) or confirmed miss (None)."""
    if value is None:
        return True
    return isinstance(value, dict) and bool(value.get("image_normal"))


def load_cache() -> dict:
    """Load image cache; drop polluted entries (e.g. color-only blobs without URLs)."""
    if not CACHE.exists():
        return {}
    raw = json.loads(CACHE.read_text(encoding="utf-8"))
    cleaned: dict = {}
    dropped = 0
    for name, value in raw.items():
        if value is None or (
            isinstance(value, dict) and value.get("image_normal")
        ):
            cleaned[name] = value
        else:
            dropped += 1
    if dropped:
        print(f"image cache: dropped {dropped} incomplete/polluted entries")
    return cleaned


def save_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def fetch_card(name: str, cache: dict) -> dict | None:
    hit = cache.get(name)
    if name in cache and _is_image_entry(hit):
        return hit
    if name in BASICS:
        cache[name] = None
        return None
    time.sleep(0.12)
    r = requests.get(
        "https://api.scryfall.com/cards/named",
        params={"exact": name},
        headers=UA,
        timeout=30,
    )
    if r.status_code == 404:
        time.sleep(0.12)
        r = requests.get(
            "https://api.scryfall.com/cards/named",
            params={"fuzzy": name},
            headers=UA,
            timeout=30,
        )
    if r.status_code == 429:
        wait = float(r.headers.get("Retry-After", "1") or 1)
        time.sleep(min(max(wait, 1.0), 60.0))
        return None
    if r.status_code == 404:
        cache[name] = None
        return None
    if r.status_code != 200:
        return None
    data = r.json()
    face = data
    if "card_faces" in data and data["card_faces"]:
        face = data["card_faces"][0]
    images = face.get("image_uris") or data.get("image_uris") or {}
    image_normal = images.get("normal")
    if not image_normal:
        # Don't cache incomplete hits — retry next run.
        return None
    entry = {
        "name": data.get("name", name),
        "set": (data.get("set") or "").upper(),
        "collector_number": data.get("collector_number") or "",
        "image_normal": image_normal,
        "image_small": images.get("small"),
        "scryfall_uri": data.get("scryfall_uri") or "",
    }
    cache[name] = entry
    return entry


def cards_payload(counts: Counter[str], cache: dict) -> list[dict]:
    cards = []
    for name, qty in sorted(counts.items(), key=lambda x: (x[0] in BASICS, x[0].lower())):
        meta = cache.get(name)
        basic = name in BASICS
        cards.append(
            {
                "name": name,
                "qty": qty,
                "basic": basic,
                "image": (meta or {}).get("image_normal") if meta else None,
                "set": (meta or {}).get("set", "") if meta else "",
                "cn": (meta or {}).get("collector_number", "") if meta else "",
                "uri": (meta or {}).get("scryfall_uri", "") if meta else "",
            }
        )
    return cards


def load_active_decks(cache: dict) -> list[dict]:
    report = ACTIVE_DIR / "report.json"
    labels: dict[str, str] = {}
    if report.exists():
        for d in json.loads(report.read_text(encoding="utf-8")).get("decks", []):
            stem = Path(d["file"]).stem
            labels[stem] = d["label"]

    out: list[dict] = []
    for path in sorted(ACTIVE_DIR.glob("0*.txt")):
        counts = parse_deck(path)
        for name in counts:
            fetch_card(name, cache)
        fallback = path.stem.split("_", 1)[1].replace("_", " ").title()
        out.append(
            {
                "id": path.stem,
                "name": labels.get(path.stem, fallback),
                "subtitle": "active",
                "cards": cards_payload(counts, cache),
            }
        )
    return out


def load_verified_decks(cache: dict, *, top_n: int) -> list[dict]:
    report_path = VERIFIED_DIR / "report.json"
    report_rows: list[dict] = []
    if report_path.exists():
        report_rows = json.loads(report_path.read_text(encoding="utf-8")).get(
            "exported", []
        )

    by_stem: dict[str, dict] = {}
    for row in report_rows:
        stem = Path(row["file"]).stem
        by_stem[stem] = row

    paths = sorted(VERIFIED_DIR.glob("0*.txt"))[: max(0, top_n)]
    out: list[dict] = []
    for rank, path in enumerate(paths, start=1):
        counts = parse_deck(path)
        for name in counts:
            fetch_card(name, cache)
        row = by_stem.get(path.stem, {})
        wr = row.get("winrate")
        games = row.get("games")
        if wr is not None and games is not None:
            name = f"#{rank} · {wr * 100:.0f}% WR · {games}g"
            subtitle = f"stub verify · elo {row.get('elo', 0):.0f}"
        else:
            name = f"#{rank} · {path.stem}"
            subtitle = "verified"
        out.append(
            {
                "id": path.stem,
                "name": name,
                "subtitle": subtitle,
                "cards": cards_payload(counts, cache),
            }
        )
    return out


HTML_TMPL = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Deck cards — finden</title>
<style>
  :root {{ --bg:#12141a; --panel:#1a1d26; --text:#e8eaed; --muted:#9aa0a6; --accent:#8ab4f8; --border:#2a2f3a; --good:#81c995; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:"IBM Plex Sans","Segoe UI",system-ui,sans-serif; background:var(--bg); color:var(--text); }}
  header {{ position:sticky; top:0; z-index:10; background:var(--panel); border-bottom:1px solid var(--border);
    padding:12px 16px; display:flex; flex-wrap:wrap; gap:10px; align-items:center; }}
  h1 {{ font-size:16px; font-weight:600; margin:0 8px 0 0; }}
  input[type=search] {{ flex:1; min-width:180px; max-width:360px; background:var(--bg); color:var(--text);
    border:1px solid var(--border); border-radius:6px; padding:8px 10px; font-size:14px; }}
  .sections, .tabs {{ display:flex; gap:6px; flex-wrap:wrap; }}
  .sections {{ width:100%; }}
  button.section, button.tab {{ background:transparent; color:var(--muted); border:1px solid var(--border);
    border-radius:999px; padding:6px 12px; cursor:pointer; font-size:13px; }}
  button.section.active {{ color:var(--text); border-color:var(--good); background:#1e3328; }}
  button.tab.active {{ color:var(--text); border-color:var(--accent); background:#243044; }}
  .meta {{ color:var(--muted); font-size:12px; width:100%; }}
  main {{ padding:16px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:12px; }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden; display:flex; flex-direction:column; }}
  .card img {{ width:100%; aspect-ratio:5/7; object-fit:cover; background:#0b0d11; display:block; }}
  .card .ph {{ width:100%; aspect-ratio:5/7; display:flex; align-items:center; justify-content:center; color:var(--muted); font-size:12px; padding:8px; text-align:center; }}
  .card .info {{ padding:8px; display:flex; flex-direction:column; gap:2px; }}
  .card .qty {{ font-weight:700; color:var(--accent); font-size:13px; }}
  .card .name {{ font-size:12px; line-height:1.3; }}
  .card .set {{ font-size:11px; color:var(--muted); }}
  a {{ color:inherit; text-decoration:none; }}
  a:hover .name {{ color:var(--accent); }}
  .empty {{ color:var(--muted); padding:24px 8px; }}
</style>
</head>
<body>
<header>
  <h1>Karten finden</h1>
  <div class="sections" id="sections"></div>
  <div class="tabs" id="tabs"></div>
  <input type="search" id="q" placeholder="Name suchen…" autocomplete="off" />
  <div class="meta" id="meta"></div>
</header>
<main><div class="grid" id="grid"></div></main>
<script>
const SECTIONS = {sections_json};
let sectionId = SECTIONS[0] ? SECTIONS[0].id : null;
let deckId = (SECTIONS[0] && SECTIONS[0].decks[0]) ? SECTIONS[0].decks[0].id : null;

function currentSection() {{
  return SECTIONS.find(s => s.id === sectionId) || SECTIONS[0];
}}
function currentDeck() {{
  const sec = currentSection();
  if (!sec) return null;
  return sec.decks.find(d => d.id === deckId) || sec.decks[0] || null;
}}
function renderSections() {{
  const el = document.getElementById('sections'); el.innerHTML = '';
  SECTIONS.forEach(s => {{
    const b = document.createElement('button');
    b.className = 'section' + (s.id === sectionId ? ' active' : '');
    b.textContent = s.label;
    b.onclick = () => {{
      sectionId = s.id;
      deckId = s.decks[0] ? s.decks[0].id : null;
      renderSections(); renderTabs(); render();
    }};
    el.appendChild(b);
  }});
}}
function renderTabs() {{
  const tabs = document.getElementById('tabs'); tabs.innerHTML = '';
  const sec = currentSection();
  if (!sec) return;
  sec.decks.forEach(d => {{
    const b = document.createElement('button');
    b.className = 'tab' + (d.id === deckId ? ' active' : '');
    b.textContent = d.name;
    b.title = d.subtitle || '';
    b.onclick = () => {{ deckId = d.id; renderTabs(); render(); }};
    tabs.appendChild(b);
  }});
}}
function render() {{
  const deck = currentDeck();
  const grid = document.getElementById('grid'); grid.innerHTML = '';
  if (!deck) {{
    document.getElementById('meta').textContent = 'Keine Decks in diesem Bereich.';
    grid.innerHTML = '<div class="empty">Keine Decks — erst export_verified_decks / active Decks erzeugen.</div>';
    return;
  }}
  const q = (document.getElementById('q').value || '').trim().toLowerCase();
  let shown = 0;
  deck.cards.forEach(c => {{
    if (q && !c.name.toLowerCase().includes(q)) return;
    shown++;
    const el = document.createElement('a');
    el.className = 'card';
    el.href = c.uri || '#';
    if (c.uri) {{ el.target = '_blank'; el.rel = 'noopener'; }}
    const img = c.image
      ? `<img src="${{c.image}}" alt="${{c.name}}" loading="lazy" />`
      : `<div class="ph">${{c.basic ? 'Basic land' : 'kein Bild'}}</div>`;
    const setline = c.set ? `${{c.set}} #${{c.cn}}` : (c.basic ? 'Basic' : '');
    el.innerHTML = `${{img}}<div class="info"><div class="qty">${{c.qty}}×</div><div class="name">${{c.name}}</div><div class="set">${{setline}}</div></div>`;
    grid.appendChild(el);
  }});
  const sec = currentSection();
  document.getElementById('meta').textContent =
    `${{sec.label}} · ${{deck.name}} · ${{shown}} Karten` +
    (deck.subtitle ? ` · ${{deck.subtitle}}` : '') +
    ' · Suche filtert · Klick → Scryfall';
}}
document.getElementById('q').addEventListener('input', render);
renderSections(); renderTabs(); render();
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="How many verified decks to include (default: 5)",
    )
    args = ap.parse_args()

    cache = load_cache()
    active = load_active_decks(cache)
    verified = load_verified_decks(cache, top_n=args.top_n)
    save_cache(cache)

    sections = [
        {
            "id": "active",
            "label": f"Active ({len(active)})",
            "decks": active,
        },
        {
            "id": "verified",
            "label": f"Verified Top {len(verified)}",
            "decks": verified,
        },
    ]

    OUT_HTML.write_text(
        HTML_TMPL.format(sections_json=json.dumps(sections, ensure_ascii=False)),
        encoding="utf-8",
    )
    names_needed = {
        c["name"]
        for sec in sections
        for d in sec["decks"]
        for c in d["cards"]
        if not c["basic"]
    }
    missing = [
        n
        for n in names_needed
        if not (cache.get(n) and cache[n] and cache[n].get("image_normal"))
    ]
    print(
        f"Wrote {OUT_HTML} active={len(active)} verified={len(verified)} "
        f"missing_images={len(missing)}"
    )
    if missing[:12]:
        print("missing sample:", missing[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
