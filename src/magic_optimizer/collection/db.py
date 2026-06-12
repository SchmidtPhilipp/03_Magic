"""SQLite schema and connection helpers for collection storage."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = os.environ.get(
    "MTG_COLLECTION_DB", str(Path("data") / "collections" / "mtg_collection.db")
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS collection_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    scryfall_id TEXT,
    card_name TEXT NOT NULL,
    set_code TEXT,
    collector_number TEXT,
    amount INTEGER NOT NULL DEFAULT 1,
    condition TEXT DEFAULT 'NM',
    language TEXT DEFAULT 'en',
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT DEFAULT '',
    UNIQUE(collection_id, card_name, set_code, collector_number, language)
);

CREATE TABLE IF NOT EXISTS scan_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    committed_at TEXT
);

CREATE TABLE IF NOT EXISTS scan_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_session_id INTEGER NOT NULL REFERENCES scan_sessions(id) ON DELETE CASCADE,
    bbox_x REAL NOT NULL,
    bbox_y REAL NOT NULL,
    bbox_w REAL NOT NULL,
    bbox_h REAL NOT NULL,
    detected_name TEXT,
    scryfall_id TEXT,
    set_code TEXT,
    confidence REAL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_collection_cards_collection
    ON collection_cards(collection_id);
CREATE INDEX IF NOT EXISTS idx_collection_cards_set
    ON collection_cards(set_code);
CREATE INDEX IF NOT EXISTS idx_scan_detections_session
    ON scan_detections(scan_session_id);
"""


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open SQLite connection with row factory."""
    path = db_path or DEFAULT_DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | None = None) -> None:
    """Create tables if they do not exist."""
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()
