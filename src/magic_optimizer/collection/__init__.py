"""Persistent collection management for MTG cards."""

from magic_optimizer.collection.db import get_connection, init_db
from magic_optimizer.collection.repository import CollectionRepository

__all__ = ["get_connection", "init_db", "CollectionRepository"]
