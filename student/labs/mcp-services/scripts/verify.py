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
FAMILIES = {"plucked_strings", "bowed_strings", "keyboards", "woodwinds", "brass", "percussion"}
SERVICES = {"sales", "repairs", "rental", "maintenance", "setup", "tuning", "restoration"}
CATEGORIES = {"delivery_delay", "instrument_quality", "repair_quality", "billing", "communication", "warranty", "rental"}
TRANSACTIONS = {"purchase", "repair", "rental", "warranty"}


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


async def domain_checks(pc, cc, partners, complaints):
    require({s for p in partners for s in p["specialties"]} == FAMILIES, "Instrument family coverage differs")
    require({s for p in partners for s in p["services"]} == SERVICES, "Music partner service coverage differs")
    require({c["category"] for c in complaints} == CATEGORIES, "Music complaint category coverage differs")
    require({c["instrument_family"] for c in complaints} == FAMILIES, "Complaint instrument family coverage differs")
    require({c["transaction_type"] for c in complaints} == TRANSACTIONS, "Complaint transaction coverage differs")
    seeded = [c for c in complaints if c["id"].startswith("complaint-") and c["id"][10:].isdigit()]
    require(len({c["product"] for c in seeded}) == 20, "Expected all 20 fictional instrument models")
    require(all(c["instrument_serial"].startswith("AVI-DEMO-") for c in seeded), "Missing synthetic instrument serial")
    for category in CATEGORIES:
        require({c["priority"] for c in seeded if c["category"] == category} == {"low", "normal", "high", "critical"},
                "Seed categories should support all priority filters")
    by_id = {p["id"]: p for p in partners}
    for complaint in seeded:
        if complaint["assigned_partner_id"]:
            partner = by_id[complaint["assigned_partner_id"]]
            required_service = {"purchase": "sales", "repair": "repairs", "rental": "rental", "warranty": "repairs"}[complaint["transaction_type"]]
            require(partner["status"] == "active" and required_service in partner["services"]
                    and complaint["instrument_family"] in partner["specialties"],
                    "Seeded complaint is assigned to an ineligible music partner")
    for service in sorted(SERVICES):
        page = await call(pc, "search_partners", {"service": service, "limit": 100})
        expected = {p["id"] for p in partners if service in p["services"]}
        require(page["total"] == len(expected) and all(p["id"] in expected for p in page["items"]), "Service filter failed")
    for family in sorted(FAMILIES):
        ppage = await call(pc, "search_partners", {"specialty": family, "limit": 100})
        cpage = await call(cc, "search_complaints", {"instrument_family": family, "limit": 100})
        require(ppage["total"] == sum(family in p["specialties"] for p in partners)
                and all(family in p["specialties"] for p in ppage["items"]), "Partner family filter failed")
        require(cpage["total"] == sum(c["instrument_family"] == family for c in complaints)
                and all(c["instrument_family"] == family for c in cpage["items"]), "Complaint family filter failed")
    for category in sorted(CATEGORIES):
        page = await call(cc, "search_complaints", {"category": category, "limit": 100})
        require(page["total"] == sum(c["category"] == category for c in complaints)
                and all(c["category"] == category for c in page["items"]), "Category filter failed")
    for transaction in sorted(TRANSACTIONS):
        page = await call(cc, "search_complaints", {"transaction_type": transaction, "limit": 100})
        require(page["total"] == sum(c["transaction_type"] == transaction for c in complaints)
                and all(c["transaction_type"] == transaction for c in page["items"]), "Transaction filter failed")
    serial = seeded[0]["instrument_serial"]
    page = await call(cc, "search_complaints", {"instrument_serial": serial.lower()})
    require(page["total"] == 1 and page["items"][0]["id"] == seeded[0]["id"], "Exact serial filter failed")
    page = await call(cc, "search_complaints", {"query": serial.lower()})
    require(page["total"] == 1, "Serial text search failed")


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
        await domain_checks(pc, cc, partners, complaints)
        seed = await call(pc, "get_partner", {"partner_id": "partner-001"})
        payload = {k: v for k, v in seed.items() if k not in {"id", "version", "updated_at"}}
        payload.update(name=f"Integration Test {suffix}", status="active", tier="gold", rating=4.9,
                       capacity_per_week=45, emergency_service=True, languages=["cs", "en"],
                       specialties=["plucked_strings", "bowed_strings"], services=["sales", "repairs", "rental"])
        new_partner, put_partner, new_complaint = None, None, None
        try:
            new_partner = await call(pc, "create_partner", {"partner": payload})
            pid = new_partner["id"]
            found = await call(pc, "search_partners", {
                "query": suffix, "country_code": "CZ", "city": "prague", "status": "active",
                "tier": "gold", "specialty": "plucked_strings", "service": "rental", "language": "CS", "emergency_service": True,
                "min_rating": 4.8, "min_capacity": 40,
            })
            require([p["id"] for p in found["items"]] == [pid], "Combined partner filters failed")
            negative = await call(pc, "search_partners", {"query": suffix, "country_code": "JP"})
            require(negative["total"] == 0, "AND filter semantics failed")
            require((await call(pc, "search_partners", {"query": suffix, "service": "restoration"}))["total"] == 0,
                    "Partner service filter ignored")
            require((await call(pc, "search_partners", {"query": "rental"}))["total"] > 0, "Service text search failed")
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
            await error(pc, "search_partners", {"specialty": "hvac"})
            await error(pc, "search_partners", {"service": "installation"})
            bad = dict(payload, rating=9)
            await error(pc, "create_partner", {"partner": bad})

            base_stats = await call(cc, "complaint_statistics")
            new_complaint = await call(cc, "create_complaint", {"complaint": {
                "customer": {"name": "Synthetic Test Customer", "email": f"{suffix}@customers.example",
                             "country_code": "CZ", "preferred_language": "cs"},
                "subject": f"Test instrument repair case {suffix}", "description": "Electric guitar output jack is still intermittent after repair.",
                "category": "repair_quality", "priority": "high", "channel": "web",
                "product": "EG-300 Switchrail solid-body electric guitar", "instrument_family": "plucked_strings",
                "instrument_serial": f"AVI-TEST-{suffix}", "transaction_type": "repair", "order_reference": f"TEST-{suffix}",
            }})
            cid = new_complaint["id"]
            require((await call(cc, "get_complaint", {"complaint_id": cid}))["status"] == "new", "New state failed")
            new_complaint = await call(cc, "update_complaint", {
                "complaint_id": cid, "patch": {"priority": "critical", "assigned_agent": "Demo Agent",
                                              "instrument_serial": f"AVI-UPDATED-{suffix}",
                                              "instrument_family": "plucked_strings", "transaction_type": "repair"},
                "expected_version": new_complaint["version"],
            })
            require(new_complaint["instrument_serial"] == f"AVI-UPDATED-{suffix}", "Instrument serial update failed")
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
                "instrument_family": "plucked_strings", "transaction_type": "repair",
                "instrument_serial": f"avi-updated-{suffix}",
            })
            require([c["id"] for c in found["items"]] == [cid], "Combined complaint search failed")
            require((await call(cc, "search_complaints", {"query": suffix, "transaction_type": "rental"}))["total"] == 0,
                    "Transaction AND filter ignored")
            require((await call(cc, "search_complaints", {"query": suffix, "instrument_family": "brass"}))["total"] == 0,
                    "Instrument family AND filter ignored")
            require((await call(cc, "search_complaints", {"instrument_serial": f"missing-{suffix}"}))["total"] == 0,
                    "Serial filter returned unrelated records")
            stats = await call(cc, "complaint_statistics")
            require(stats["total"] == base_stats["total"] + 1, "Statistics total failed")
            require(stats["by_instrument_family"]["plucked_strings"] == base_stats["by_instrument_family"]["plucked_strings"] + 1
                    and stats["by_transaction_type"]["repair"] == base_stats["by_transaction_type"]["repair"] + 1,
                    "Music-domain statistics failed")
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
            await error(cc, "search_complaints", {"category": "late_arrival"})
            await error(cc, "search_complaints", {"transaction_type": "installation"})
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
    print(f"PASS ({mode}): 6 partner tools + 10 complaint tools; music-domain data, all service/family/category/transaction/serial filters, CRUD, lifecycle, errors, cleanup")


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
