# openosint/case_db.py
"""
SQLite-backed Case persistence for OpenOSINT.

Stores investigation cases with: id (UUID), name, timestamps, and JSON blobs
for messages, chat_history, current_targets, and graph data.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CaseDB:
    """SQLite CRUD for investigation cases."""

    CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS cases (
            id              TEXT    PRIMARY KEY,
            name            TEXT    NOT NULL,
            created_at      TEXT    NOT NULL,
            updated_at      TEXT    NOT NULL,
            messages        TEXT    NOT NULL DEFAULT '[]',
            chat_history    TEXT    NOT NULL DEFAULT '[]',
            current_targets TEXT    NOT NULL DEFAULT '[]',
            graph           TEXT    NOT NULL DEFAULT '{}'
        )
    """

    CREATE_INDEX = """
        CREATE INDEX IF NOT EXISTS idx_cases_updated_at
        ON cases(updated_at DESC)
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Create the cases table and indexes."""
        conn = self._connect()
        conn.execute(self.CREATE_TABLE)
        conn.execute(self.CREATE_INDEX)
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_case(self, name: str) -> dict[str, Any]:
        """Create a new case and return its full record."""
        now = self._now()
        case_id = str(uuid.uuid4())
        conn = self._connect()
        cursor = conn.execute(
            """INSERT INTO cases (id, name, created_at, updated_at, messages,
               chat_history, current_targets, graph)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (case_id, name, now, now, "[]", "[]", "[]", "{}"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        """Return full case record by ID, or None if not found."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM cases WHERE id = ?", (case_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_cases(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return case summaries sorted by updated_at DESC (newest first).

        Summaries exclude the large JSON blobs (messages, chat_history, graph)
        to keep list responses lightweight.
        """
        conn = self._connect()
        rows = conn.execute(
            """SELECT id, name, created_at, updated_at
               FROM cases
               ORDER BY updated_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_case(
        self, case_id: str, **fields: str
    ) -> dict[str, Any] | None:
        """Update one or more fields on an existing case.

        Accepts any column name as a keyword argument (e.g. messages, graph).
        Always bumps updated_at. Returns the full updated record or None.
        """
        # Only allow known updatable columns.
        allowed = {
            "messages", "chat_history", "current_targets", "graph", "name",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_case(case_id)

        now = self._now()
        updates["updated_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [case_id]

        conn = self._connect()
        cursor = conn.execute(
            f"UPDATE cases SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return None
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def rename_case(self, case_id: str, name: str) -> dict[str, Any] | None:
        """Rename a case. Returns the updated record or None."""
        return self.update_case(case_id, name=name)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_case(self, case_id: str) -> bool:
        """Delete a case by ID. Returns True if it existed, False otherwise."""
        conn = self._connect()
        cursor = conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
