"""Exercise every tool through real HTTP; leave only seed records behind."""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from dotenv import dotenv_values
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
import httpx2

ROOT = Path(__file__).resolve().parents[1]
PARTNER_TOOLS = {"get_partner", "list_partners", "search_partners", "create_partner", "put_partner", "delete_partner"}
COMPLAINT_TOOLS = {"get_complaint", "list_complaints", "search_complaints", "create_complaint",
                   "update_complaint", "assign_complaint", "add_complaint_note", "transition_complaint",
                   "complaint_statistics", "delete_complaint"}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def fresh_http_client(**kwargs):
    # Express can retire an HTTP connection during stop/start or idle scaling.
    return httpx2.AsyncClient(**kwargs, limits=httpx2.Limits(max_keepalive_connections=0))


def mcp_client(url, key, mode="auto"):
    transport = StreamableHttpTransport(url, auth=key, httpx_client_factory=fresh_http_client)
    return Client(transport, timeout=60, init_timeout=90, mode=mode)


def http_checks(url: str):
    origin = url.removesuffix("/mcp")
    with urlopen(origin + "/healthz", timeout=60) as response:
        require(json.load(response)["status"] == "ok", "Health failed")
    for method in ("GET", "POST", "DELETE"):
        for auth in (None, "deliberately-invalid-token"):
            headers = {"Accept": "application/json, text/event-stream"}
            if auth:
                headers["Authorization"] = f"Bearer {auth}"
            request = Request(url, data=b"{}" if method == "POST" else None, headers=headers, method=method)
            try:
                with urlopen(request, timeout=60):
                    raise AssertionError(f"Unauthenticated {method} unexpectedly succeeded")
            except HTTPError as exc:
                require(exc.code == 401, f"Expected 401 for {method}, got {exc.code}")


async def call(client, name, arguments=None):
    try:
        result = await client.call_tool(name, arguments or {})
    except httpx2.TransportError:
        print(f"Transport failure in {name}; mutation outcome may be uncertain. Inspect records before retrying.", file=sys.stderr)
        raise
    if result.structured_content is not None:
        return result.structured_content
    return json.loads(result.content[0].text)


async def error(client, name, arguments, contains=None):
    result = await client.call_tool(name, arguments, raise_on_error=False)
    require(result.is_error, f"{name} should fail")
    if contains:
        require(contains in str(result.content), f"Expected '{contains}' in tool error")


async def all_pages(client, tool):
    items, offset = [], 0
    while True:
        page = await call(client, tool, {"offset": offset, "limit": 37})
        require(len(page["items"]) <= 37, "Page limit ignored")
        items.extend(page["items"])
        if page["next_offset"] is None:
            require(len(items) == page["total"], "Pagination lost records")
            require(len({item["id"] for item in items}) == len(items), "Duplicate page records")
            return items
        offset = page["next_offset"]


async def journey(partner_url, complaint_url, key, mode="auto"):
    suffix = uuid4().hex[:12]
    async with mcp_client(partner_url, key, mode) as pc, mcp_client(complaint_url, key, mode) as cc:
        require({t.name for t in await pc.list_tools()} == PARTNER_TOOLS, "Partner discovery differs")
        require({t.name for t in await cc.list_tools()} == COMPLAINT_TOOLS, "Complaint discovery differs")
        if mode == "legacy":
            await pc.ping()
            await cc.ping()
        partners = await all_pages(pc, "list_partners")
        complaints = await all_pages(cc, "list_complaints")
        require(len(partners) >= 120, "Fewer than 120 partner seeds")
        require(len(complaints) >= 90, "Fewer than 90 complaint seeds")
        require(len({p["address"]["country_code"] for p in partners}) >= 20, "Insufficient geographic variety")
        seed = await call(pc, "get_partner", {"partner_id": "partner-001"})
        payload = {k: v for k, v in seed.items() if k not in {"id", "version", "updated_at"}}
        payload.update(name=f"Integration Test {suffix}", status="active", tier="gold", rating=4.9,
                       capacity_per_week=45, emergency_service=True, languages=["cs", "en"],
                       specialties=["hvac", "solar"])
        new_partner, put_partner, new_complaint = None, None, None
        try:
            new_partner = await call(pc, "create_partner", {"partner": payload})
            pid = new_partner["id"]
            found = await call(pc, "search_partners", {
                "query": suffix, "country_code": "CZ", "city": "prague", "status": "active",
                "tier": "gold", "specialty": "solar", "language": "CS", "emergency_service": True,
                "min_rating": 4.8, "min_capacity": 40,
            })
            require([p["id"] for p in found["items"]] == [pid], "Combined partner filters failed")
            negative = await call(pc, "search_partners", {"query": suffix, "country_code": "JP"})
            require(negative["total"] == 0, "AND filter semantics failed")
            put_partner = await call(pc, "put_partner", {"partner_id": f"test-{suffix}", "partner": payload})
            payload["capacity_per_week"] = 46
            put_partner = await call(pc, "put_partner", {
                "partner_id": put_partner["id"], "partner": payload, "expected_version": 1,
            })
            require(put_partner["version"] == 2 and put_partner["capacity_per_week"] == 46, "PUT replacement failed")
            same = await call(pc, "put_partner", {
                "partner_id": put_partner["id"], "partner": payload, "expected_version": 2,
            })
            require(same == put_partner, "Identical PUT is not idempotent")
            await error(pc, "put_partner", {"partner_id": put_partner["id"], "partner": payload}, "expected_version")
            await error(pc, "put_partner", {"partner_id": put_partner["id"], "partner": payload, "expected_version": 1}, "Version conflict")
            await error(pc, "delete_partner", {"partner_id": pid, "expected_version": 999}, "Version conflict")
            await error(pc, "get_partner", {"partner_id": f"missing-{suffix}"}, "Not found")
            await error(pc, "list_partners", {"limit": 101})
            await error(pc, "search_partners", {"min_rating": 6})
            bad = dict(payload, rating=9)
            await error(pc, "create_partner", {"partner": bad})

            base_stats = await call(cc, "complaint_statistics")
            new_complaint = await call(cc, "create_complaint", {"complaint": {
                "customer": {"name": "Synthetic Test Customer", "email": f"{suffix}@customers.example",
                             "country_code": "CZ", "preferred_language": "cs"},
                "subject": f"Test service case {suffix}", "description": "Synthetic repair-quality issue",
                "category": "repair_quality", "priority": "high", "channel": "web",
                "product": "Heat pump", "order_reference": f"TEST-{suffix}",
            }})
            cid = new_complaint["id"]
            require((await call(cc, "get_complaint", {"complaint_id": cid}))["status"] == "new", "New state failed")
            new_complaint = await call(cc, "update_complaint", {
                "complaint_id": cid, "patch": {"priority": "critical", "assigned_agent": "Demo Agent"},
                "expected_version": new_complaint["version"],
            })
            new_complaint = await call(cc, "assign_complaint", {
                "complaint_id": cid, "partner_id": pid, "agent": "Demo Agent",
                "expected_version": new_complaint["version"],
            })
            new_complaint = await call(cc, "add_complaint_note", {
                "complaint_id": cid, "author": "Demo Agent", "text": "Confirmed active partner and planned a visit.",
                "expected_version": new_complaint["version"],
            })
            require(len(new_complaint["notes"]) == 1, "Note append failed")
            found = await call(cc, "search_complaints", {
                "query": suffix, "status": "new", "priority": "critical", "category": "repair_quality",
                "country_code": "CZ", "partner_id": pid, "customer_email": f"{suffix}@customers.example",
            })
            require([c["id"] for c in found["items"]] == [cid], "Combined complaint search failed")
            stats = await call(cc, "complaint_statistics")
            require(stats["total"] == base_stats["total"] + 1, "Statistics total failed")
            overdue = await call(cc, "search_complaints", {"overdue_only": True, "limit": 100})
            require(all(c["status"] not in {"resolved", "closed"} for c in overdue["items"]), "Overdue includes closed cases")
            await error(cc, "transition_complaint", {
                "complaint_id": cid, "status": "closed", "reason": "Invalid shortcut",
                "expected_version": new_complaint["version"],
            }, "Invalid transition")
            await error(cc, "update_complaint", {"complaint_id": cid, "patch": {}, "expected_version": new_complaint["version"]}, "non-null")
            await error(cc, "update_complaint", {"complaint_id": cid, "patch": {"subject": None}, "expected_version": new_complaint["version"]}, "non-null")
            await error(cc, "update_complaint", {"complaint_id": cid, "patch": {"priority": "low"}, "expected_version": 1}, "Version conflict")
            for status in ["triaged", "in_progress", "awaiting_customer", "in_progress", "resolved", "closed", "triaged", "in_progress", "resolved", "in_progress", "resolved", "closed"]:
                arguments = {"complaint_id": cid, "status": status, "reason": f"Verified {status}",
                             "expected_version": new_complaint["version"]}
                if status == "resolved":
                    await error(cc, "transition_complaint", arguments, "resolution is required")
                    arguments["resolution"] = "Synthetic follow-up repair accepted"
                new_complaint = await call(cc, "transition_complaint", arguments)
                require(new_complaint["status"] == status, f"Transition to {status} failed")
            require(len(new_complaint["history"]) == 12, "History is incomplete")
            await error(cc, "assign_complaint", {"complaint_id": cid, "partner_id": pid, "agent": "Demo Agent",
                                                "expected_version": new_complaint["version"]}, "Reopen")
            await error(cc, "get_complaint", {"complaint_id": f"missing-{suffix}"}, "Not found")
            await error(cc, "list_complaints", {"offset": -1})
            await error(cc, "delete_complaint", {"complaint_id": cid, "expected_version": 1}, "Version conflict")
        finally:
            # Refresh versions so a failed assertion does not leave successful writes behind.
            for client, row, get, delete, field in [
                (cc, new_complaint, "get_complaint", "delete_complaint", "complaint_id"),
                (pc, put_partner, "get_partner", "delete_partner", "partner_id"),
                (pc, new_partner, "get_partner", "delete_partner", "partner_id"),
            ]:
                if row:
                    current = await call(client, get, {field: row["id"]})
                    result = await call(client, delete, {field: row["id"], "expected_version": current["version"]})
                    require(result["deleted"], "Test cleanup failed")
                    await error(client, get, {field: row["id"]}, "Not found")
        require((await call(pc, "list_partners"))["total"] == len(partners), "Partner cleanup count mismatch")
        require((await call(cc, "list_complaints"))["total"] == len(complaints), "Complaint cleanup count mismatch")
    print(f"PASS ({mode}): 6 partner tools + 10 complaint tools; pagination, filters, CRUD, lifecycle, errors, cleanup")


async def verify(partner_url, complaint_url, key):
    await asyncio.to_thread(http_checks, partner_url)
    await asyncio.to_thread(http_checks, complaint_url)
    await journey(partner_url, complaint_url, key)
    await journey(partner_url, complaint_url, key, mode="legacy")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--partners")
    parser.add_argument("--complaints")
    parser.add_argument("--state", type=Path, default=ROOT / ".deployment.json")
    args = parser.parse_args()
    key = os.environ.get("MCP_API_KEY") or dotenv_values(ROOT / ".env").get("MCP_API_KEY")
    if not key:
        parser.error("Set MCP_API_KEY or create the ignored .env")
    if args.partners and args.complaints:
        urls = args.partners, args.complaints
    elif args.partners or args.complaints:
        parser.error("Provide both URLs")
    else:
        state = json.loads(args.state.read_text())
        urls = state["partners_url"], state["complaints_url"]
    started = time.monotonic()
    asyncio.run(verify(*urls, key))
    print(f"PASS: authenticated remote HTTP, anonymous/invalid keys denied; elapsed {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    main()
