"""Prepare one seat's MCP connections and filtered toolbox; never deploy infrastructure."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

BACKEND = Path(__file__).resolve().parents[2] / "mcp-services"
sys.path.insert(0, str(BACKEND / "scripts"))
from dotenv import dotenv_values

ARM_VERSION = "2026-07-01"
ALLOWLIST = {
    "partners": ["get_partner", "search_partners"],
    "complaints": ["get_complaint", "search_complaints", "create_complaint",
                   "assign_complaint", "add_complaint_note"],
}


class Foundry:
    def __init__(self, key):
        self.key = key
        self.tokens = {}
        self.az = shutil.which("az")
        if not self.az:
            raise RuntimeError("Azure CLI is required; sign in to the authorized subscription first")

    def request(self, url, method="GET", data=None, *, arm=False, missing=False):
        audience = "https://management.azure.com" if arm else "https://ai.azure.com"
        if audience not in self.tokens:
            result = subprocess.run(
                [self.az, "account", "get-access-token", "--resource", audience, "-o", "json"],
                text=True, capture_output=True, timeout=60, check=False,
            )
            if result.returncode:
                raise RuntimeError("Azure token acquisition failed: " + result.stderr[:1500])
            self.tokens[audience] = json.loads(result.stdout)["accessToken"]
        body = json.dumps(data).encode() if data is not None else None
        try:
            with urlopen(Request(url, body, {
                "Authorization": "Bearer " + self.tokens[audience], "Content-Type": "application/json",
            }, method=method), timeout=90) as response:
                content = response.read()
                return json.loads(content) if content else {}
        except HTTPError as error:
            if missing and error.code == 404:
                return None
            message = error.read().decode(errors="replace")
            for secret in [self.key, *self.tokens.values()]:
                message = message.replace(secret, "[redacted]")
            correlation = error.headers.get("x-ms-request-id") or error.headers.get("apim-request-id")
            raise RuntimeError(f"{method} HTTP {error.code}; correlation={correlation}; {message[:1500]}") from None


def project_paths(endpoint, resource_id):
    endpoint = endpoint.rstrip("/")
    url = urlsplit(endpoint)
    match = re.fullmatch(r"/subscriptions/([^/]+)/resourceGroups/([^/]+)/providers/Microsoft.CognitiveServices/accounts/([^/]+)/projects/([^/]+)", resource_id, re.IGNORECASE)
    if not match:
        raise ValueError("Supply the exact Foundry project's ARM resource ID")
    account, project = match.group(3), match.group(4)
    if (url.scheme != "https" or url.hostname != account.lower() + ".services.ai.azure.com"
            or url.path != "/api/projects/" + project or url.query or url.fragment or url.username or url.port):
        raise ValueError("Project endpoint and ARM resource ID do not match")
    return endpoint, "https://management.azure.com" + resource_id


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def ensure_connection(client, arm, name, properties, owner):
    url = arm + "/connections/" + name + "?api-version=" + ARM_VERSION
    current = client.request(url, arm=True, missing=True)
    if current:
        existing = current["properties"]
        if existing.get("metadata", {}).get("lab04_owner") != owner:
            raise RuntimeError("Refusing existing connection without matching ownership: " + name)
        for field in ("category", "target", "authType", "audience", "isSharedToAll"):
            if field in properties and existing.get(field) != properties[field]:
                raise RuntimeError(f"Owned connection differs at {field}: {name}; inspect before changing it")
        return
    client.request(url, "PUT", {"properties": properties}, arm=True)


def prepare(args):
    endpoint, arm = project_paths(args.project_endpoint, args.project_resource_id)
    if not re.fullmatch(r"S[0-9]{2,3}", args.seat):
        raise ValueError("Seat must be S plus two or three digits, for example S07")
    if not args.confirm:
        raise ValueError("Pass --confirm to authorize three new connections and one toolbox; no infrastructure changes")
    if not args.state.resolve().is_relative_to(BACKEND.parents[2] / ".workshop"):
        raise ValueError("Keep the private --state receipt under the repository's ignored .workshop directory")
    key = os.environ.get("MCP_API_KEY") or dotenv_values(BACKEND / ".env").get("MCP_API_KEY")
    if not key:
        raise ValueError("Prepare the existing backend's ignored .env or MCP_API_KEY; never pass a key on the command line")
    deployment = json.loads((BACKEND / ".deployment.json").read_text())
    client = Foundry(key)
    client.request(arm + "?api-version=" + ARM_VERSION, arm=True)
    owner = "foundry-workshop-lab04-" + args.seat.lower()
    prefix = "lab04-" + args.seat.lower()
    state = {"owner": owner, "seat": args.seat, "project_endpoint": endpoint,
             "project_resource_id": args.project_resource_id, "toolbox": prefix + "-tools",
             "connections": [prefix + "-partners", prefix + "-complaints", prefix + "-toolbox"],
             "status": "preparing"}
    if args.state.exists():
        previous = json.loads(args.state.read_text())
        if any(previous.get(k) != state[k] for k in ("owner", "seat", "project_endpoint", "project_resource_id")):
            raise RuntimeError("State belongs to another scope; choose a separate private --state path")
    save(args.state, state)
    print("Scope:", args.seat, "three project connections and toolbox", state["toolbox"])
    print("No agents, roles, deployments, monitoring or backend records are changed.")
    tools = []
    for service, names in ALLOWLIST.items():
        server_url = deployment[service + "_url"]
        parsed = urlsplit(server_url)
        if (parsed.scheme != "https" or parsed.path != "/mcp" or not parsed.hostname
                or parsed.username or parsed.query or parsed.fragment):
            raise ValueError("Invalid deployed HTTPS MCP endpoint for " + service)
        name = prefix + "-" + service
        ensure_connection(client, arm, name, {
            "category": "RemoteTool", "target": server_url, "authType": "CustomKeys",
            "credentials": {"keys": {"Authorization": "Bearer " + key}},
            "metadata": {"lab04_owner": owner}, "isSharedToAll": False,
        }, owner)
        tools.append({"type": "mcp", "server_label": service, "server_url": server_url,
                      "project_connection_id": name, "allowed_tools": names,
                      "require_approval": "always", "description": "Synthetic instrument " + service})
        print("Verified connection:", name)
    toolbox_url = endpoint + "/toolboxes/" + state["toolbox"]
    current = client.request(toolbox_url + "?api-version=v1", missing=True)
    if current:
        version = str(current["default_version"])
        box = client.request(toolbox_url + "/versions/" + version + "?api-version=v1")
        if box.get("metadata", {}).get("lab04_owner") != owner:
            raise RuntimeError("Refusing toolbox without matching ownership")
        actual = box.get("tools", [])
        if len(actual) != len(tools) or any(
            any(a.get(k) != v for k, v in expected.items())
            for a, expected in zip(actual, tools)
        ):
            raise RuntimeError("Owned toolbox configuration differs; inspect before creating/promoting another version")
    else:
        box = client.request(toolbox_url + "/versions?api-version=v1", "POST", {
            "metadata": {"lab04_owner": owner}, "description": "Lab 04 curated instrument tools", "tools": tools,
        })
        version = str(box["version"])
    state["toolbox_version"] = version
    state["toolbox_mcp_endpoint"] = toolbox_url + "/versions/" + version + "/mcp?api-version=v1"
    save(args.state, state)
    ensure_connection(client, arm, prefix + "-toolbox", {
        "category": "RemoteTool", "target": state["toolbox_mcp_endpoint"],
        "authType": "UserEntraToken", "audience": "https://ai.azure.com",
        "metadata": {"lab04_owner": owner}, "isSharedToAll": False,
    }, owner)
    state["status"] = "configured-not-qualified"
    save(args.state, state)
    print("PASS: configuration saved to", args.state)
    print("Qualify discovery, approvals, actual agent calls and traces with the intended attendee identity before delivery.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-endpoint", required=True)
    parser.add_argument("--project-resource-id", required=True)
    parser.add_argument("--seat", required=True)
    parser.add_argument("--state", type=Path, required=True, help="Private ignored JSON receipt for this exact seat")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    prepare(args)


if __name__ == "__main__":
    main()
