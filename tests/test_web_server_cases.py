"""Tests for the CaseDB REST API endpoints in web_server.py.

Landed from the only surviving copy (blackwood worktree t_63e0e65f, kanban
night-burn-2026-11-02 lane 6) and adapted to the FINAL merged contract:

- GET /api/cases returns {"cases": [...]} (the draft asserted a bare list).
- DELETE returns 204 with no body (the draft asserted 200 + {"deleted": true}).
- Name validation (empty / max length) does NOT exist in the shipped models,
  so those draft assertions are replaced with tests that pin the shipped
  behaviour. If validation is later added, flip these three tests.
- Isolation: create_app() wires CaseDB at _ROOT/"data"/cases.db, so the
  fixture monkeypatches openosint.web_server._ROOT to tmp_path — the live
  data/cases.db is never touched (the draft's OPENOSINT_DATA_DIR env var is
  not read by the shipped code).

Uses httpx ASGITransport to hit the FastAPI app directly — no network needed.
"""

from __future__ import annotations

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from openosint import web_server
from openosint.web_server import create_app

NOT_FOUND_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
async def client(tmp_path, monkeypatch):
    """Async client bound to a fresh app with an isolated tmp CaseDB."""
    monkeypatch.setattr(web_server, "_ROOT", tmp_path)
    app = create_app()
    # The DB file must live under tmp_path — guards the isolation patch.
    assert (tmp_path / "data" / "cases.db").exists()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create(client, name: str) -> str:
    resp = await client.post("/api/cases", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# GET /api/cases
# ---------------------------------------------------------------------------


class TestListCases:
    async def test_empty_list(self, client):
        resp = await client.get("/api/cases")
        assert resp.status_code == 200
        assert resp.json() == {"cases": []}

    async def test_returns_summaries(self, client):
        await _create(client, "Alpha")
        await _create(client, "Beta")
        resp = await client.get("/api/cases")
        assert resp.status_code == 200
        data = resp.json()["cases"]
        assert len(data) == 2
        # Summaries exclude the large JSON blobs but carry UI preview fields.
        for summary in data:
            assert "messages" not in summary
            assert "chat_history" not in summary
            assert "graph" not in summary
            assert "current_targets" in summary
            assert "message_count" in summary
        # Newest first (updated_at DESC).
        assert data[0]["name"] == "Beta"


# ---------------------------------------------------------------------------
# POST /api/cases
# ---------------------------------------------------------------------------


class TestCreateCase:
    async def test_create_returns_201(self, client):
        resp = await client.post("/api/cases", json={"name": "New Investigation"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Investigation"
        assert len(data["id"]) == 36
        uuid.UUID(data["id"])  # valid UUID

    async def test_create_has_defaults(self, client):
        resp = await client.post("/api/cases", json={"name": "Defaults"})
        data = resp.json()
        assert json.loads(data["messages"]) == []
        assert json.loads(data["chat_history"]) == []
        assert json.loads(data["current_targets"]) == []
        assert json.loads(data["graph"]) == {}

    async def test_create_missing_name_rejected(self, client):
        resp = await client.post("/api/cases", json={})
        assert resp.status_code == 422

    async def test_create_empty_and_long_names_accepted(self, client):
        # Shipped contract: CreateCaseRequest.name is a plain `str` — no
        # min_length / max_length validation exists. Pins current behaviour.
        assert (
            await client.post("/api/cases", json={"name": ""})
        ).status_code == 201
        assert (
            await client.post("/api/cases", json={"name": "x" * 201})
        ).status_code == 201


# ---------------------------------------------------------------------------
# GET /api/cases/{id}
# ---------------------------------------------------------------------------


class TestGetCase:
    async def test_get_full_case(self, client):
        case_id = await _create(client, "GetMe")
        resp = await client.get(f"/api/cases/{case_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == case_id
        assert "messages" in data
        assert "graph" in data

    async def test_get_nonexistent(self, client):
        resp = await client.get(f"/api/cases/{NOT_FOUND_ID}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/cases/{id}
# ---------------------------------------------------------------------------


class TestUpdateCase:
    async def test_update_messages(self, client):
        case_id = await _create(client, "Update")
        msgs = json.dumps([{"role": "user", "content": "hello"}])
        resp = await client.put(f"/api/cases/{case_id}", json={"messages": msgs})
        assert resp.status_code == 200
        assert json.loads(resp.json()["messages"]) == [
            {"role": "user", "content": "hello"}
        ]

    async def test_update_graph(self, client):
        case_id = await _create(client, "Graph")
        graph = json.dumps({"nodes": [{"id": "ip:8.8.8.8"}], "edges": []})
        resp = await client.put(f"/api/cases/{case_id}", json={"graph": graph})
        assert resp.status_code == 200
        assert json.loads(resp.json()["graph"]) == {
            "nodes": [{"id": "ip:8.8.8.8"}],
            "edges": [],
        }

    async def test_update_partial_preserves_others(self, client):
        case_id = await _create(client, "Partial")
        resp = await client.put(f"/api/cases/{case_id}", json={"graph": "{}"})
        data = resp.json()
        assert data["name"] == "Partial"
        assert data["messages"] == "[]"

    async def test_update_chat_history(self, client):
        case_id = await _create(client, "Chat")
        history = json.dumps([{"role": "assistant", "content": "hi"}])
        resp = await client.put(
            f"/api/cases/{case_id}", json={"chat_history": history}
        )
        assert resp.status_code == 200
        assert json.loads(resp.json()["chat_history"]) == [
            {"role": "assistant", "content": "hi"}
        ]

    async def test_update_current_targets(self, client):
        case_id = await _create(client, "Targets")
        targets = json.dumps(["8.8.8.8"])
        resp = await client.put(
            f"/api/cases/{case_id}", json={"current_targets": targets}
        )
        assert resp.status_code == 200
        assert json.loads(resp.json()["current_targets"]) == ["8.8.8.8"]

    async def test_update_nonexistent(self, client):
        resp = await client.put(
            f"/api/cases/{NOT_FOUND_ID}",
            json={"messages": "[]"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/cases/{id}/name
# ---------------------------------------------------------------------------


class TestRenameCase:
    async def test_rename(self, client):
        case_id = await _create(client, "Old")
        resp = await client.patch(f"/api/cases/{case_id}/name", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    async def test_rename_nonexistent(self, client):
        resp = await client.patch(
            f"/api/cases/{NOT_FOUND_ID}/name", json={"name": "Nope"}
        )
        assert resp.status_code == 404

    async def test_rename_empty_name_accepted(self, client):
        # Shipped contract: RenameCaseRequest.name is a plain `str` — no
        # validation exists. Pins current behaviour; flip if validation lands.
        case_id = await _create(client, "X")
        resp = await client.patch(f"/api/cases/{case_id}/name", json={"name": ""})
        assert resp.status_code == 200
        assert resp.json()["name"] == ""


# ---------------------------------------------------------------------------
# DELETE /api/cases/{id}
# ---------------------------------------------------------------------------


class TestDeleteCase:
    async def test_delete_existing(self, client):
        case_id = await _create(client, "Gone")
        resp = await client.delete(f"/api/cases/{case_id}")
        assert resp.status_code == 204
        assert (await client.get(f"/api/cases/{case_id}")).status_code == 404

    async def test_delete_nonexistent(self, client):
        resp = await client.delete(f"/api/cases/{NOT_FOUND_ID}")
        assert resp.status_code == 404
