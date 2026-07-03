#!/usr/bin/env python3
"""Integration test for PATCH /api/cases/{id}/name endpoint."""
import asyncio
import tempfile
import sys
from pathlib import Path

from httpx import AsyncClient, ASGITransport


async def main():
    # Import app factory
    from openosint.web_server import create_app

    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create a case
        resp = await client.post("/api/cases", json={"name": "Test Case"})
        assert resp.status_code == 201, f"POST create failed: {resp.status_code} {resp.text}"
        case_id = resp.json()["id"]
        print(f"OK: created case {case_id}")

        # 2. PATCH rename
        resp = await client.patch(
            f"/api/cases/{case_id}/name", json={"name": "Renamed Case"}
        )
        assert resp.status_code == 200, f"PATCH rename failed: {resp.status_code} {resp.text}"
        assert resp.json()["name"] == "Renamed Case"
        print("OK: PATCH rename to 'Renamed Case'")

        # 3. Verify with GET
        resp = await client.get(f"/api/cases/{case_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Case"
        print("OK: GET verifies renamed name")

        # 4. 404 for non-existent case
        resp = await client.patch(
            "/api/cases/non-existent/name", json={"name": "Nope"}
        )
        assert resp.status_code == 404
        print("OK: 404 for non-existent case")

        print("\nAll PATCH rename endpoint tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
