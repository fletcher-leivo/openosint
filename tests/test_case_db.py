# tests/test_case_db.py
"""
Tests for the SQLite CaseDB persistence module.

Uses temporary databases via tempfile so tests are isolated and leave
no artifacts on disk.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from openosint.case_db import CaseDB


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Return a unique database file path for each test."""
    return str(tmp_path / "test_cases.db")


@pytest.fixture
def db(db_path: str) -> CaseDB:
    """Create an empty CaseDB with schema already initialized."""
    instance = CaseDB(db_path)
    instance.init_schema()
    return instance


# ---------------------------------------------------------------------------
# init_schema
# ---------------------------------------------------------------------------


class TestInitSchema:
    def test_creates_cases_table(self, db: CaseDB, db_path: str):
        """init_schema creates the 'cases' table in the database."""
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cases'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_expected_columns(self, db: CaseDB, db_path: str):
        """The 'cases' table has all required columns."""
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(cases)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "id", "name", "created_at", "updated_at",
            "messages", "chat_history", "current_targets", "graph",
        }
        assert expected.issubset(columns)
        conn.close()

    def test_is_idempotent(self, db: CaseDB):
        """Calling init_schema multiple times does not error."""
        db.init_schema()
        db.init_schema()  # Should not raise


# ---------------------------------------------------------------------------
# create_case
# ---------------------------------------------------------------------------


class TestCreateCase:
    def test_creates_case_with_name(self, db: CaseDB):
        """create_case returns a case dict with a UUID and the given name."""
        case = db.create_case("Test Investigation")
        assert case["id"] is not None
        assert len(case["id"]) == 36  # UUID-4 format
        assert case["name"] == "Test Investigation"
        assert case["created_at"] is not None
        assert case["updated_at"] is not None

    def test_default_empty_json_fields(self, db: CaseDB):
        """New cases have empty JSON arrays for messages, chat_history, targets, graph."""
        case = db.create_case("Empty Case")
        assert json.loads(case["messages"]) == []
        assert json.loads(case["chat_history"]) == []
        assert json.loads(case["current_targets"]) == []
        assert json.loads(case["graph"]) == {}

    def test_multiple_cases_have_unique_ids(self, db: CaseDB):
        """Each create_case call generates a unique UUID."""
        c1 = db.create_case("Case A")
        c2 = db.create_case("Case B")
        assert c1["id"] != c2["id"]


# ---------------------------------------------------------------------------
# get_case
# ---------------------------------------------------------------------------


class TestGetCase:
    def test_returns_existing_case(self, db: CaseDB):
        """get_case returns the case that was created."""
        created = db.create_case("Lookup Case")
        fetched = db.get_case(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["name"] == "Lookup Case"

    def test_returns_none_for_missing_id(self, db: CaseDB):
        """get_case returns None for a nonexistent ID."""
        result = db.get_case("nonexistent-id")
        assert result is None

    def test_json_fields_are_strings(self, db: CaseDB):
        """JSON fields come back as JSON-encoded strings, not parsed objects."""
        case = db.create_case("JSON Test")
        fetched = db.get_case(case["id"])
        assert isinstance(fetched["messages"], str)
        assert isinstance(fetched["chat_history"], str)
        assert isinstance(fetched["current_targets"], str)
        assert isinstance(fetched["graph"], str)


# ---------------------------------------------------------------------------
# update_case
# ---------------------------------------------------------------------------


class TestUpdateCase:
    def test_update_messages(self, db: CaseDB):
        """update_case can update the messages field."""
        case = db.create_case("Update Test")
        msgs = json.dumps([{"role": "user", "content": "hello"}])
        updated = db.update_case(case["id"], messages=msgs)
        assert json.loads(updated["messages"]) == [{"role": "user", "content": "hello"}]

    def test_partial_update_preserves_other_fields(self, db: CaseDB):
        """Updating one field does not overwrite unchanged fields."""
        case = db.create_case("Partial Test")
        graph = json.dumps({"nodes": [], "edges": []})
        updated = db.update_case(case["id"], graph=graph)
        assert updated["name"] == "Partial Test"
        assert json.loads(updated["graph"]) == {"nodes": [], "edges": []}

    def test_update_touched_timestamp(self, db: CaseDB):
        """update_case increments the updated_at timestamp."""
        import time
        case = db.create_case("Timestamp Test")
        old_updated = case["updated_at"]
        time.sleep(0.05)
        updated = db.update_case(case["id"], messages="[]")
        assert updated["updated_at"] >= old_updated

    def test_update_nonexistent_returns_none(self, db: CaseDB):
        """update_case on a missing ID returns None."""
        result = db.update_case("fake-id", messages="[]")
        assert result is None

    def test_update_chat_history(self, db: CaseDB):
        """update_case can update chat_history."""
        case = db.create_case("Chat Test")
        history = json.dumps([{"role": "assistant", "content": "hi"}])
        updated = db.update_case(case["id"], chat_history=history)
        assert json.loads(updated["chat_history"]) == [{"role": "assistant", "content": "hi"}]

    def test_update_current_targets(self, db: CaseDB):
        """update_case can update current_targets."""
        case = db.create_case("Targets Test")
        targets = json.dumps(["8.8.8.8", "1.1.1.1"])
        updated = db.update_case(case["id"], current_targets=targets)
        assert json.loads(updated["current_targets"]) == ["8.8.8.8", "1.1.1.1"]


# ---------------------------------------------------------------------------
# rename_case
# ---------------------------------------------------------------------------


class TestRenameCase:
    def test_renames_existing_case(self, db: CaseDB):
        """rename_case updates the case name."""
        case = db.create_case("Old Name")
        updated = db.rename_case(case["id"], "New Name")
        assert updated["name"] == "New Name"

    def test_rename_nonexistent_returns_none(self, db: CaseDB):
        """rename_case on a missing ID returns None."""
        result = db.rename_case("fake-id", "Nope")
        assert result is None


# ---------------------------------------------------------------------------
# delete_case
# ---------------------------------------------------------------------------


class TestDeleteCase:
    def test_deletes_existing_case(self, db: CaseDB):
        """delete_case removes the case and returns True."""
        case = db.create_case("ToDelete")
        assert db.delete_case(case["id"]) is True
        assert db.get_case(case["id"]) is None

    def test_delete_nonexistent_returns_false(self, db: CaseDB):
        """delete_case on a missing ID returns False."""
        assert db.delete_case("fake-id") is False


# ---------------------------------------------------------------------------
# list_cases
# ---------------------------------------------------------------------------


class TestListCases:
    def test_empty_list_when_no_cases(self, db: CaseDB):
        """list_cases returns [] when no cases exist."""
        assert db.list_cases() == []

    def test_returns_summaries_sorted_by_updated(self, db: CaseDB):
        """list_cases returns cases sorted by updated_at descending."""
        import time
        c1 = db.create_case("First")
        time.sleep(0.05)
        c2 = db.create_case("Second")
        cases = db.list_cases()
        assert len(cases) == 2
        assert cases[0]["id"] == c2["id"]  # Second created later = higher updated_at
        assert cases[1]["id"] == c1["id"]

    def test_respects_limit(self, db: CaseDB):
        """list_cases(limit=N) returns at most N cases."""
        for i in range(5):
            db.create_case(f"Case {i}")
        cases = db.list_cases(limit=3)
        assert len(cases) == 3

    def test_summaries_contain_expected_keys(self, db: CaseDB):
        """list_case summaries have id, name, created_at, updated_at."""
        case = db.create_case("Summary Test")
        cases = db.list_cases()
        summary = cases[0]
        assert "id" in summary
        assert "name" in summary
        assert "created_at" in summary
        assert "updated_at" in summary

    def test_summaries_do_not_contain_full_data(self, db: CaseDB):
        """list_case summaries do NOT include messages, chat_history, graph blobs."""
        case = db.create_case("Blobs Test")
        db.update_case(
            case["id"],
            messages=json.dumps([{"role": "user", "content": "big data"}]),
        )
        summary = db.list_cases()[0]
        assert "messages" not in summary
        assert "chat_history" not in summary
        assert "graph" not in summary
