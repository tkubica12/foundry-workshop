"""Verify that an Express stop/start actually discards in-memory mutations."""
import argparse
import asyncio
import json
import os
import subprocess
import sys

from dotenv import dotenv_values
from verify import ROOT, call, mcp_client, error, require, verify


async def seed_edits(state, key):
    async with mcp_client(state["partners_url"], key) as pc, mcp_client(state["complaints_url"], key) as cc:
        seed = await call(pc, "get_partner", {"partner_id": "partner-001"})
        payload = {k: v for k, v in seed.items() if k not in {"id", "version", "updated_at"}}
        payload["name"] = "Synthetic Music Partner Reset Verification"
        partner = await call(pc, "create_partner", {"partner": payload})
        complaint = await call(cc, "create_complaint", {"complaint": {
            "customer": {"name": "Reset Test", "email": "reset@customers.example", "country_code": "CZ"},
            "subject": "Instrument repair reset sentinel", "description": "This synthetic guitar repair case must disappear after reset.",
            "category": "communication", "product": "EG-300 Switchrail solid-body electric guitar",
            "instrument_family": "plucked_strings", "transaction_type": "repair",
            "instrument_serial": "AVI-RESET-TEST", "order_reference": "RESET-TEST",
        }})
        return partner["id"], complaint["id"]


async def assert_reset(state, key, identifiers):
    async with mcp_client(state["partners_url"], key) as pc, mcp_client(state["complaints_url"], key) as cc:
        await error(pc, "get_partner", {"partner_id": identifiers[0]}, "Not found")
        await error(cc, "get_complaint", {"complaint_id": identifiers[1]}, "Not found")
        require((await call(pc, "list_partners"))["total"] == 120, "Partner seed count not restored")
        require((await call(cc, "list_complaints"))["total"] == 90, "Complaint seed count not restored")
    await verify(state["partners_url"], state["complaints_url"], key)


def main():
    parser = argparse.ArgumentParser(description="Destructive to all runtime mock edits in both apps")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("Pass --confirm to authorize loss of all in-memory edits")
    state = json.loads((ROOT / ".deployment.json").read_text())
    key = os.environ.get("MCP_API_KEY") or dotenv_values(ROOT / ".env").get("MCP_API_KEY")
    if not key:
        parser.error("Configure MCP_API_KEY or .env")
    identifiers = asyncio.run(seed_edits(state, key))
    print(f"Created reset sentinels: {identifiers[0]}, {identifiers[1]}", flush=True)
    result = subprocess.run([sys.executable, "-u", str(ROOT / "scripts" / "azure.py"), "reset",
                             "--subscription", state["subscription"],
                             "--resource-group", state["resource_group"], "--confirm"],
                            timeout=1800, check=False)
    if result.returncode:
        raise RuntimeError(f"Reset failed; inspect recovery marker and sentinel records {identifiers}")
    asyncio.run(assert_reset(state, key, identifiers))
    print("PASS: both sentinel writes disappeared and exact seed counts were restored")


if __name__ == "__main__":
    main()
