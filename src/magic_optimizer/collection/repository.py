"""CRUD operations for collections and cards."""

from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd

from magic_optimizer.collection.db import get_connection, init_db


class CollectionRepository:
    """SQLite-backed collection store."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        init_db(db_path)

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def ensure_user(self, external_id: str, display_name: str | None = None) -> int:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT id FROM users WHERE external_id = ?", (external_id,)
            ).fetchone()
            if row:
                return int(row["id"])
            cur = conn.execute(
                "INSERT INTO users (external_id, display_name) VALUES (?, ?)",
                (external_id, display_name or external_id),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def list_collections(self, user_id: int) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT c.*,
                       (SELECT COUNT(*) FROM collection_cards cc
                        WHERE cc.collection_id = c.id) AS card_count
                FROM collections c
                WHERE c.user_id = ?
                ORDER BY c.updated_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def create_collection(
        self, user_id: int, name: str, description: str = ""
    ) -> dict[str, Any]:
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO collections (user_id, name, description)
                VALUES (?, ?, ?)
                """,
                (user_id, name.strip(), description.strip()),
            )
            conn.commit()
            return self.get_collection(int(cur.lastrowid), user_id) or {}
        finally:
            conn.close()

    def get_collection(
        self, collection_id: int, user_id: int | None = None
    ) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            if user_id is not None:
                row = conn.execute(
                    """
                    SELECT c.*,
                           (SELECT COUNT(*) FROM collection_cards cc
                            WHERE cc.collection_id = c.id) AS card_count
                    FROM collections c
                    WHERE c.id = ? AND c.user_id = ?
                    """,
                    (collection_id, user_id),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT c.*,
                           (SELECT COUNT(*) FROM collection_cards cc
                            WHERE cc.collection_id = c.id) AS card_count
                    FROM collections c
                    WHERE c.id = ?
                    """,
                    (collection_id,),
                ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_collection(self, collection_id: int, user_id: int) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                "DELETE FROM collections WHERE id = ? AND user_id = ?",
                (collection_id, user_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def list_cards(
        self,
        collection_id: int,
        user_id: int,
        set_code: str | None = None,
    ) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            if not self.get_collection(collection_id, user_id):
                return []
            query = """
                SELECT cc.*
                FROM collection_cards cc
                JOIN collections c ON c.id = cc.collection_id
                WHERE cc.collection_id = ? AND c.user_id = ?
            """
            params: list[Any] = [collection_id, user_id]
            if set_code:
                query += " AND UPPER(cc.set_code) = UPPER(?)"
                params.append(set_code)
            query += " ORDER BY cc.card_name, cc.set_code"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def add_card(
        self,
        collection_id: int,
        user_id: int,
        *,
        card_name: str,
        amount: int = 1,
        set_code: str | None = None,
        collector_number: str | None = None,
        scryfall_id: str | None = None,
        source: str = "manual",
        language: str = "en",
        condition: str = "NM",
        notes: str = "",
    ) -> dict[str, Any] | None:
        if not self.get_collection(collection_id, user_id):
            return None
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO collection_cards (
                    collection_id, scryfall_id, card_name, set_code,
                    collector_number, amount, condition, language, source, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(collection_id, card_name, set_code, collector_number, language)
                DO UPDATE SET
                    amount = amount + excluded.amount,
                    scryfall_id = COALESCE(excluded.scryfall_id, scryfall_id),
                    notes = CASE
                        WHEN excluded.notes != '' THEN excluded.notes
                        ELSE notes
                    END
                """,
                (
                    collection_id,
                    scryfall_id,
                    card_name.strip(),
                    set_code,
                    collector_number,
                    max(1, amount),
                    condition,
                    language,
                    source,
                    notes,
                ),
            )
            conn.execute(
                "UPDATE collections SET updated_at = datetime('now') WHERE id = ?",
                (collection_id,),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT * FROM collection_cards
                WHERE collection_id = ? AND card_name = ?
                  AND IFNULL(set_code,'') = IFNULL(?, '')
                  AND IFNULL(collector_number,'') = IFNULL(?, '')
                  AND language = ?
                """,
                (
                    collection_id,
                    card_name.strip(),
                    set_code,
                    collector_number,
                    language,
                ),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def remove_card(self, card_id: int, collection_id: int, user_id: int) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                DELETE FROM collection_cards
                WHERE id = ? AND collection_id = ?
                  AND collection_id IN (
                      SELECT id FROM collections WHERE user_id = ?
                  )
                """,
                (card_id, collection_id, user_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def import_csv(
        self, collection_id: int, user_id: int, df: pd.DataFrame
    ) -> int:
        """Import rows from a Moxfield/Card Kingdom style CSV. Returns rows added."""
        if not self.get_collection(collection_id, user_id):
            return 0
        added = 0
        name_col = _pick_column(df, ("card_name", "Name", "name"))
        if not name_col:
            raise ValueError("CSV must contain a card name column")
        amount_col = _pick_column(df, ("amount", "Quantity", "quantity"))
        set_col = _pick_column(df, ("set_code", "Set", "set"))
        num_col = _pick_column(
            df, ("collector_number", "Collector Number", "number")
        )
        for _, row in df.iterrows():
            name = str(row[name_col]).strip()
            if not name or name.lower() == "nan":
                continue
            amount = 1
            if amount_col and pd.notna(row.get(amount_col)):
                try:
                    amount = int(row[amount_col])
                except (TypeError, ValueError):
                    amount = 1
            set_code = None
            if set_col and pd.notna(row.get(set_col)):
                set_code = str(row[set_col]).strip() or None
            collector_number = None
            if num_col and pd.notna(row.get(num_col)):
                collector_number = str(row[num_col]).strip() or None
            self.add_card(
                collection_id,
                user_id,
                card_name=name,
                amount=amount,
                set_code=set_code,
                collector_number=collector_number,
                source="csv",
            )
            added += 1
        return added

    def distinct_sets(self, collection_id: int, user_id: int) -> list[str]:
        conn = self._conn()
        try:
            if not self.get_collection(collection_id, user_id):
                return []
            rows = conn.execute(
                """
                SELECT DISTINCT UPPER(set_code) AS set_code
                FROM collection_cards
                WHERE collection_id = ? AND set_code IS NOT NULL AND set_code != ''
                ORDER BY set_code
                """,
                (collection_id,),
            ).fetchall()
            return [str(r["set_code"]) for r in rows]
        finally:
            conn.close()

    def to_optimizer_dataframe(
        self,
        collection_id: int,
        user_id: int,
        set_codes: list[str] | None = None,
        card_ids: list[int] | None = None,
    ) -> pd.DataFrame:
        """Export collection subset in optimizer-compatible CSV shape."""
        cards = self.list_cards(collection_id, user_id)
        if set_codes:
            allowed = {s.upper() for s in set_codes}
            cards = [
                c
                for c in cards
                if c.get("set_code") and c["set_code"].upper() in allowed
            ]
        if card_ids is not None:
            allowed_ids = set(card_ids)
            cards = [c for c in cards if c["id"] in allowed_ids]
        rows = []
        for c in cards:
            for _ in range(int(c.get("amount") or 1)):
                rows.append(
                    {
                        "Name": c["card_name"],
                        "Set": c.get("set_code") or "",
                        "Collector Number": c.get("collector_number") or "",
                    }
                )
        return pd.DataFrame(rows)


def _pick_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None
