"""Build an updatable union inventory from scan summaries + collection CSVs."""

from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from magic_optimizer.vision.identify import is_junk_match, normalize_card_name
from magic_optimizer.vision.scryfall import lookup_card_name

ROOT = Path(__file__).resolve().parents[3]


@dataclass
class CardAgg:
    card_name: str
    amount: int = 0
    scryfall_id: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    language: str = "en"
    sources: set[str] = field(default_factory=set)
    scan_hits: int = 0
    csv_amount: int = 0
    csv_by_source: dict[str, int] = field(default_factory=dict)
    uncertain_hits: int = 0

    def merge_key(self) -> str:
        # Name-level union (scans lack reliable printing); printings kept as metadata.
        return self.card_name.strip().lower()

    def finalize_csv_amount(self) -> int:
        """Across overlapping CSV inventories use max; within one file we already summed."""
        if not self.csv_by_source:
            self.csv_amount = 0
        else:
            self.csv_amount = max(self.csv_by_source.values())
        return self.csv_amount


def _strip_uncertain(name: str) -> tuple[str, bool]:
    n = (name or "").strip()
    if n.startswith("? "):
        return n[2:].strip(), True
    if n.startswith("?"):
        return n[1:].strip(), True
    return n, False


def load_scan_summary(
    path: Path, *, source_id: str, include_uncertain: bool = False
) -> list[tuple[str, bool, str]]:
    """Return [(card_name, uncertain, provenance), ...] from batch_eval summary."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[tuple[str, bool, str]] = []
    for img in data.get("per_image") or []:
        file_stem = Path(str(img.get("file") or "unknown")).stem
        for raw in img.get("names") or []:
            name, uncertain = _strip_uncertain(str(raw))
            name = normalize_card_name(name)
            if not name or name.lower() in {"unbekannt", "unknown"}:
                continue
            if is_junk_match(name):
                continue
            # detect-only labels look like "binder_yolo:0.92"
            if re.fullmatch(r"[\w-]+:[0-9.]+", name):
                continue
            if uncertain and not include_uncertain:
                continue
            out.append((name, uncertain, f"{source_id}:{file_stem}"))
    return out


def load_moxfield_csv(path: Path, *, source_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("card_name") or row.get("Name") or "").strip()
            if not name:
                continue
            try:
                amount = int(row.get("amount") or row.get("Quantity") or 1)
            except ValueError:
                amount = 1
            rows.append(
                {
                    "card_name": normalize_card_name(name),
                    "amount": max(1, amount),
                    "set_code": (row.get("set_code") or row.get("Set code") or "")
                    .strip()
                    .upper()
                    or None,
                    "collector_number": (
                        row.get("collector_number")
                        or row.get("Collector number")
                        or ""
                    ).strip()
                    or None,
                    "scryfall_id": (
                        row.get("Scryfall ID") or row.get("scryfall_id") or ""
                    ).strip()
                    or None,
                    "language": (row.get("language") or row.get("Language") or "en")
                    .strip()
                    .lower()
                    or "en",
                    "source_id": source_id,
                }
            )
    return rows


def build_union(
    *,
    scan_summaries: Iterable[tuple[Path, str]],
    csv_paths: Iterable[tuple[Path, str]],
    include_uncertain: bool = False,
    resolve_scryfall: bool = True,
    scryfall_sleep: float = 0.05,
) -> dict[str, Any]:
    """
    Union inventory by oracle card name.

    amount = max(scan_hits, csv_amount) so overlapping CSV + binder photos
    do not double-count the same physical collection. Multiple CSV exports
    that overlap (e.g. ManaBox partial + full) use max(per-source totals).
    """
    aggs: dict[str, CardAgg] = {}

    def ensure(name: str) -> CardAgg:
        key = name.strip().lower()
        if key not in aggs:
            aggs[key] = CardAgg(card_name=name.strip())
        return aggs[key]

    sources_meta: list[dict[str, Any]] = []

    for path, sid in scan_summaries:
        if not path.exists():
            continue
        hits = load_scan_summary(
            path, source_id=sid, include_uncertain=include_uncertain
        )
        sources_meta.append(
            {
                "id": sid,
                "type": "scan_summary",
                "path": str(path),
                "detections_used": len(hits),
            }
        )
        for name, uncertain, prov in hits:
            a = ensure(name)
            a.sources.add(prov)
            if uncertain:
                a.uncertain_hits += 1
            else:
                a.scan_hits += 1

    for path, sid in csv_paths:
        if not path.exists():
            continue
        rows = load_moxfield_csv(path, source_id=sid)
        sources_meta.append(
            {
                "id": sid,
                "type": "csv",
                "path": str(path),
                "rows": len(rows),
            }
        )
        for row in rows:
            a = ensure(row["card_name"])
            a.sources.add(sid)
            a.csv_by_source[sid] = a.csv_by_source.get(sid, 0) + int(row["amount"])
            if row.get("scryfall_id") and not a.scryfall_id:
                a.scryfall_id = row["scryfall_id"]
            if row.get("set_code") and not a.set_code:
                a.set_code = row["set_code"]
            if row.get("collector_number") and not a.collector_number:
                a.collector_number = row["collector_number"]
            if row.get("language"):
                a.language = row["language"]

    for a in aggs.values():
        a.finalize_csv_amount()

    if resolve_scryfall:
        for a in aggs.values():
            if a.scryfall_id:
                continue
            meta = lookup_card_name(a.card_name)
            if meta:
                a.scryfall_id = meta.get("scryfall_id")
                a.set_code = a.set_code or meta.get("set_code")
                a.collector_number = a.collector_number or meta.get(
                    "collector_number"
                )
                # Prefer Scryfall canonical name
                if meta.get("card_name"):
                    a.card_name = meta["card_name"]
            if scryfall_sleep:
                time.sleep(scryfall_sleep)

    cards: list[dict[str, Any]] = []
    for a in sorted(aggs.values(), key=lambda x: x.card_name.lower()):
        amount = max(a.scan_hits, a.csv_amount)
        if amount <= 0 and a.uncertain_hits:
            # only uncertain hits — skip unless include_uncertain counted into scan
            continue
        if amount <= 0:
            continue
        cards.append(
            {
                "card_name": a.card_name,
                "amount": amount,
                "scryfall_id": a.scryfall_id,
                "set_code": a.set_code,
                "collector_number": a.collector_number,
                "language": a.language,
                "scan_hits": a.scan_hits,
                "csv_amount": a.csv_amount,
                "uncertain_hits": a.uncertain_hits,
                "sources": sorted(a.sources),
            }
        )

    return {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "merge_policy": (
            "amount = max(scan_hits, max(csv_per_source)) by card_name; "
            "overlapping CSV inventories do not sum"
        ),
        "sources": sources_meta,
        "stats": {
            "unique_cards": len(cards),
            "total_copies": sum(c["amount"] for c in cards),
            "scan_only": sum(
                1 for c in cards if c["scan_hits"] and not c["csv_amount"]
            ),
            "csv_only": sum(
                1 for c in cards if c["csv_amount"] and not c["scan_hits"]
            ),
            "both": sum(
                1 for c in cards if c["scan_hits"] and c["csv_amount"]
            ),
        },
        "cards": cards,
    }


def write_union_outputs(union: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "union_collection.json"
    csv_path = out_dir / "union_collection.csv"
    json_path.write_text(
        json.dumps(union, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "amount",
                "card_name",
                "set_code",
                "collector_number",
                "scryfall_id",
                "language",
                "scan_hits",
                "csv_amount",
                "sources",
            ],
        )
        writer.writeheader()
        for c in union["cards"]:
            writer.writerow(
                {
                    "amount": c["amount"],
                    "card_name": c["card_name"],
                    "set_code": c.get("set_code") or "",
                    "collector_number": c.get("collector_number") or "",
                    "scryfall_id": c.get("scryfall_id") or "",
                    "language": c.get("language") or "en",
                    "scan_hits": c.get("scan_hits") or 0,
                    "csv_amount": c.get("csv_amount") or 0,
                    "sources": ";".join(c.get("sources") or []),
                }
            )
    return {"json": json_path, "csv": csv_path}


def sync_union_to_sqlite(
    union: dict[str, Any],
    *,
    db_path: str | None = None,
    user_external_id: str = "local",
    collection_name: str = "Union Collection",
) -> int:
    """Replace cards in a named SQLite collection with the union snapshot."""
    from magic_optimizer.collection.repository import CollectionRepository

    repo = CollectionRepository(db_path)
    user_id = repo.ensure_user(user_external_id, display_name=user_external_id)
    existing = [
        c
        for c in repo.list_collections(user_id)
        if c.get("name") == collection_name
    ]
    if existing:
        collection_id = int(existing[0]["id"])
        # wipe cards for clean replace (re-runnable)
        conn = repo._conn()
        try:
            conn.execute(
                "DELETE FROM collection_cards WHERE collection_id = ?",
                (collection_id,),
            )
            conn.commit()
        finally:
            conn.close()
    else:
        created = repo.create_collection(
            user_id,
            collection_name,
            description="Auto union of binder scans + CSV collections (rebuildable)",
        )
        collection_id = int(created["id"])

    n = 0
    for c in union["cards"]:
        repo.add_card(
            collection_id,
            user_id,
            card_name=c["card_name"],
            amount=int(c["amount"]),
            set_code=c.get("set_code"),
            collector_number=c.get("collector_number"),
            scryfall_id=c.get("scryfall_id"),
            language=c.get("language") or "en",
            source="union",
            notes=f"scan={c.get('scan_hits', 0)};csv={c.get('csv_amount', 0)}",
        )
        n += 1
    return n
