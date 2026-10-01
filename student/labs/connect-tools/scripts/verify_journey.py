"""Operator-only MCP rehearsal. Never certify Foundry or portal traces from this check."""
import argparse
import asyncio
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[2] / "mcp-services"
sys.path.insert(0, str(BACKEND / "scripts"))
from dotenv import dotenv_values
from verify import call, mcp_client, require

PARTNERS = {"get_partner", "search_partners"}
COMPLAINTS = {"get_complaint", "search_complaints", "create_complaint",
              "assign_complaint", "add_complaint_note"}


def eligible(partner, complaint):
    service = {"repair": "repairs", "warranty": "repairs", "purchase": "sales", "rental": "rental"}[complaint["transaction_type"]]
    return (partner["status"] == "active"
            and partner["address"]["country_code"] == complaint["customer"]["country_code"]
            and complaint["instrument_family"] in partner["specialties"]
            and service in partner["services"])


async def journey(partners_url, complaints_url, key, write=False):
    marker = "LAB04-VERIFY-" + uuid4().hex[:12]
    created_id = None
    async with mcp_client(partners_url, key) as pc, mcp_client(complaints_url, key) as cc:
        require(PARTNERS <= {t.name for t in await pc.list_tools()}, "Partner discovery is missing a lab tool")
        require(COMPLAINTS <= {t.name for t in await cc.list_tools()}, "Complaint discovery is missing a lab tool")
        seed = await call(cc, "get_complaint", {"complaint_id": "complaint-003"})
        matches = await call(pc, "search_partners", {
            "country_code": seed["customer"]["country_code"], "status": "active",
            "specialty": seed["instrument_family"],
            "service": {"repair": "repairs", "warranty": "repairs", "purchase": "sales", "rental": "rental"}[seed["transaction_type"]],
        })
        require(matches["items"], "Read scenario has no eligible partner")
        partner = await call(pc, "get_partner", {"partner_id": matches["items"][0]["id"]})
        require(eligible(partner, seed), "Read scenario partner is not eligible")
        print("PASS: seed complaint read, filtered partner search and exact eligibility check; no seed writes")
        if not write:
            return
        print("Scope: create, assign, note and delete ONE generated complaint; order_reference=" + marker)
        print("No partners, seeded complaints, Foundry resources or cloud infrastructure will be changed.")
        try:
            require((await call(cc, "search_complaints", {"query": marker}))["total"] == 0, "Marker already exists")
            row = await call(cc, "create_complaint", {"complaint": {
                "customer": {"name": "Alex Lab", "email": "alex.lab@example.com", "country_code": "CZ", "preferred_language": "en"},
                "subject": marker + " guitar repair follow-up",
                "description": "The fictional guitar still buzzes after a repair. No real booking.",
                "category": "repair_quality", "priority": "normal", "channel": "chat",
                "product": "EG-300 Switchrail solid-body electric guitar",
                "instrument_family": "plucked_strings", "instrument_serial": "AVI-DEMO-" + marker,
                "transaction_type": "repair", "order_reference": marker,
            }})
            created_id = row["id"]
            print("Created complaint_id=" + created_id)
            require(row["version"] == 1 and row["status"] == "new", "Unexpected initial case state")
            candidates = await call(pc, "search_partners", {
                "country_code": "CZ", "status": "active", "specialty": "plucked_strings", "service": "repairs",
            })
            require(candidates["items"], "No eligible CZ repair partner")
            chosen = await call(pc, "get_partner", {"partner_id": candidates["items"][0]["id"]})
            require(eligible(chosen, row), "Selected partner is not eligible")
            before = await call(cc, "get_complaint", {"complaint_id": created_id})
            row = await call(cc, "assign_complaint", {
                "complaint_id": created_id, "partner_id": chosen["id"],
                "agent": "Lab verification", "expected_version": before["version"],
            })
            require(row["version"] == 2 and row["assigned_partner_id"] == chosen["id"], "Assignment failed")
            before = await call(cc, "get_complaint", {"complaint_id": created_id})
            row = await call(cc, "add_complaint_note", {
                "complaint_id": created_id, "author": "Lab verification",
                "text": "Synthetic follow-up assessment requested; no real booking or contact was made.",
                "expected_version": before["version"],
            })
            after = await call(cc, "get_complaint", {"complaint_id": created_id})
            require(after["version"] == 3 and after["status"] == "new", "Readback state differs")
            require(after["assigned_partner_id"] == chosen["id"] and len(after["notes"]) == 1, "Readback write evidence missing")
            stale = await cc.call_tool("assign_complaint", {
                "complaint_id": created_id, "partner_id": chosen["id"],
                "agent": "Lab verification", "expected_version": 1,
            }, raise_on_error=False)
            require(stale.is_error and "Version conflict" in str(stale.content), "Stale version was accepted")
            require((await call(cc, "get_complaint", {"complaint_id": created_id}))["version"] == 3, "Conflict changed the case")
            print("PASS: exact lab create, assignment, note, independent readback and stale-version rejection")
        finally:
            if created_id:
                row = await call(cc, "get_complaint", {"complaint_id": created_id})
                require(row["order_reference"] == marker, "Cleanup ownership mismatch; record retained")
                await call(cc, "delete_complaint", {"complaint_id": created_id, "expected_version": row["version"]})
                require((await call(cc, "search_complaints", {"query": marker}))["total"] == 0, "Cleanup readback failed")
                print("PASS: deleted only generated complaint " + created_id)
            else:
                print("No known created ID. If a create timed out, inspect order_reference=" + marker + " before retrying.")


def local(write):
    processes = []
    key = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="lab04-") as folder:
        handles = []
        try:
            urls = []
            for service in ("partners", "complaints"):
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                log = open(Path(folder) / (service + ".log"), "w+")
                handles.append(log)
                proc = subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", "services." + service + ":app",
                     "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
                    cwd=BACKEND, env=dict(os.environ, MCP_API_KEY=key, PYTHONNOUSERSITE="1"),
                    stdout=log, stderr=log,
                )
                processes.append(proc)
                origin = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 90
                while True:
                    if proc.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(service + " startup failed: " + log.read())
                    try:
                        with urlopen(origin + "/healthz", timeout=2):
                            break
                    except (URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise TimeoutError(service + " startup timed out")
                        time.sleep(0.5)
                urls.append(origin + "/mcp")
            asyncio.run(journey(*urls, key, write))
        finally:
            for proc in processes:
                if proc.poll() is None:
                    proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=15)
            for handle in handles:
                handle.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", action="store_true", help="Use two clean loopback processes and a random temporary key")
    parser.add_argument("--confirm", action="store_true", help="Authorize one generated synthetic write journey and exact cleanup")
    args = parser.parse_args()
    if args.local:
        local(args.confirm)
    else:
        key = os.environ.get("MCP_API_KEY") or dotenv_values(BACKEND / ".env").get("MCP_API_KEY")
        if not key:
            parser.error("Set MCP_API_KEY or prepare the existing backend's ignored .env")
        state = json.loads((BACKEND / ".deployment.json").read_text())
        asyncio.run(journey(state["partners_url"], state["complaints_url"], key, args.confirm))
    print("This verifies direct MCP only, not Foundry integration, approvals, telemetry or portal navigation.")


if __name__ == "__main__":
    main()
