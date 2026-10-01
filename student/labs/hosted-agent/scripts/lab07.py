"""Scoped Hosted Agent lifecycle. Configuration and receipts stay in .workshop."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentEndpointProtocol, AgentVersionStatus, ContainerConfiguration, HostedAgentDefinition, ProtocolVersionRecord,
)
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import AzureCliCredential

ROOT = Path(__file__).resolve().parents[4]
PRIVATE = ROOT / ".workshop" / "hosted-agent"
ENVIRONMENT = {
    "TOOLBOX_ENDPOINT", "PARTNERS_MCP_URL", "COMPLAINTS_MCP_URL", "MCP_API_KEY",
    "LAB07_RECORD_CONTENT", "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT",
}


def private_path(path: Path) -> Path:
    path = path.resolve()
    if not path.is_relative_to(PRIVATE.resolve()) or path.suffix != ".json":
        raise ValueError("Keep configuration and receipts as JSON under .workshop/hosted-agent")
    return path


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_config(path: Path) -> dict:
    config = json.loads(private_path(path).read_text(encoding="utf-8"))
    if set(config) != {
        "project_endpoint", "project_resource_id", "agent_name", "owner", "model", "image", "environment",
    }:
        raise ValueError("Configuration fields must match config.example.json exactly")
    if not all(isinstance(config[key], str) and config[key].strip() for key in config if key != "environment"):
        raise ValueError("Configuration identifiers, model and image must be nonempty strings")
    owner = config["owner"]
    if not re.fullmatch(r"lab07-[a-z0-9-]{3,32}", owner):
        raise ValueError("Use a lowercase lab07-<unique-run> owner")
    if not re.fullmatch(re.escape(owner) + r"-s[0-9]{2,3}", config["agent_name"]):
        raise ValueError("Agent name must be <owner>-sNN")
    arm = re.fullmatch(
        r"/subscriptions/([0-9a-f-]{36})/resourceGroups/([^/]+)/providers/"
        r"Microsoft.CognitiveServices/accounts/([^/]+)/projects/([^/]+)",
        config["project_resource_id"], re.IGNORECASE,
    )
    if not arm:
        raise ValueError("Supply the exact project ARM ID")
    if config["project_endpoint"] != f"https://{arm[3]}.services.ai.azure.com/api/projects/{arm[4]}":
        raise ValueError("Project endpoint and ARM ID must match")
    if not re.fullmatch(r"[a-z0-9.-]+/[a-z0-9_./-]+@sha256:[a-f0-9]{64}", config["image"]):
        raise ValueError("Use a lower-case immutable image reference by sha256 digest")
    env = config["environment"]
    if not isinstance(env, dict) or not set(env) <= ENVIRONMENT or not all(isinstance(v, str) and v for v in env.values()):
        raise ValueError("Only nonempty approved runtime environment values are allowed")
    endpoint = config["project_endpoint"]
    if "TOOLBOX_ENDPOINT" in env:
        if any(k in env for k in ("MCP_API_KEY", "PARTNERS_MCP_URL", "COMPLAINTS_MCP_URL")):
            raise ValueError("Choose toolbox or direct MCP, not both")
        if not re.fullmatch(
            re.escape(endpoint) + r"/toolboxes/[a-zA-Z0-9_-]+/versions/[0-9]+/mcp\?api-version=v1",
            env["TOOLBOX_ENDPOINT"],
        ):
            raise ValueError("Use a version-pinned toolbox in the same project")
    else:
        if not {"MCP_API_KEY", "PARTNERS_MCP_URL", "COMPLAINTS_MCP_URL"} <= set(env):
            raise ValueError("Provide a toolbox or both existing MCP services and a connection placeholder")
        if not re.fullmatch(r"\$\{\{connections\.[a-zA-Z0-9_-]+\.credentials\.[a-zA-Z0-9_-]+\}\}", env["MCP_API_KEY"]):
            raise ValueError("MCP_API_KEY must be a Foundry connection placeholder, never a literal secret")
        for key in ("PARTNERS_MCP_URL", "COMPLAINTS_MCP_URL"):
            url = urlsplit(env[key])
            if url.scheme != "https" or not url.hostname or url.username or url.password or url.path != "/mcp" or url.query or url.fragment:
                raise ValueError("Direct MCP endpoints must be credential-free HTTPS /mcp URLs")
    config["_subscription"] = arm[1]
    return config


def fingerprint(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def checked_version(project, config, receipt):
    version = project.agents.get_version(config["agent_name"], receipt["version"])
    if version.metadata.get("lab07_owner") != config["owner"] or version.metadata.get("lab07_config") != fingerprint(config):
        raise RuntimeError("Live ownership or configuration differs; refusing operation")
    return version


def version_status(version) -> str:
    status = version.status
    return status.value if isinstance(status, AgentVersionStatus) else status


def wait_active(project, config, receipt, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        version = checked_version(project, config, receipt)
        status = version_status(version)
        receipt["status"] = status
        save(receipt["_path"], {k: v for k, v in receipt.items() if k != "_path"})
        print("Version", receipt["version"], "status", status, flush=True)
        if status == "active":
            return version
        if status in {"failed", "deleted", "deleting"}:
            raise RuntimeError(f"Hosted version is {status}; inspect Foundry provisioning diagnostics before retrying")
        time.sleep(10)
    raise TimeoutError("Activation timed out; version retained, rerun status rather than redeploy")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["preflight", "deploy", "status", "cleanup"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if not 30 <= args.timeout <= 900:
        raise ValueError("Timeout must be 30..900 seconds")
    return args


def run(args):
    config = read_config(args.config)
    state = private_path(args.state)
    if args.config.resolve() == state:
        raise ValueError("Configuration and receipt must be separate files")
    az = shutil.which("az")
    if not az:
        raise RuntimeError("Azure CLI is required")
    account = subprocess.run([az, "account", "show", "--query", "id", "-o", "tsv"],
                             capture_output=True, text=True, timeout=60, check=True)
    if account.stdout.strip().lower() != config["_subscription"].lower():
        raise RuntimeError("Active subscription differs from the authorized configuration")
    print("Scope:", config["agent_name"], config["image"], flush=True)
    print("No backend, toolbox, model, shared registry or role changes.", flush=True)
    with AIProjectClient(
        endpoint=config["project_endpoint"], credential=AzureCliCredential(process_timeout=60),
        allow_preview=True,
        retry_total=0, connection_timeout=20, read_timeout=90,
    ) as project:
        if args.operation == "preflight":
            list(project.connections.list())
            print("PASS: configuration and project access; deployment/runtime/monitoring access still need qualification")
            return
        receipt = json.loads(state.read_text(encoding="utf-8")) if state.exists() else None
        if receipt and receipt.get("config") != fingerprint(config):
            raise RuntimeError("Receipt belongs to a different configuration; do not overwrite it")
        if args.operation == "deploy":
            if not args.confirm:
                raise ValueError("Pass --confirm to create the named agent/version")
            if receipt:
                if "version" not in receipt:
                    raise RuntimeError("Previous create outcome is uncertain; inspect owned live versions and recover the receipt before retrying")
                wait_active(project, config, {**receipt, "_path": state}, args.timeout)
                return
            try:
                project.agents.get(config["agent_name"])
            except ResourceNotFoundError:
                pass
            else:
                raise RuntimeError("Agent name already exists; choose a new isolated name")
            receipt = {"config": fingerprint(config), "agent": config["agent_name"], "owner": config["owner"], "status": "create-requested"}
            save(state, receipt)
            definition = HostedAgentDefinition(
                cpu="1", memory="2Gi",
                protocol_versions=[ProtocolVersionRecord(protocol=AgentEndpointProtocol.RESPONSES, version="2.0.0")],
                container_configuration=ContainerConfiguration(image=config["image"]),
                environment_variables={"MODEL_DEPLOYMENT_NAME": config["model"], **config["environment"]},
            )
            version = project.agents.create_version(
                config["agent_name"], definition=definition,
                metadata={"lab07_owner": config["owner"], "lab07_config": fingerprint(config)},
                description="Optional Lab 07: read-only LangGraph instrument specialist",
            )
            receipt.update(version=str(version.version), status=version_status(version))
            save(state, receipt)
            wait_active(project, config, {**receipt, "_path": state}, args.timeout)
        elif args.operation == "status":
            if not receipt or "version" not in receipt:
                raise RuntimeError("No known version; inspect the project without creating another one")
            wait_active(project, config, {**receipt, "_path": state}, args.timeout)
        else:
            if not args.confirm:
                raise ValueError("Pass --confirm to delete only the recorded owned version and its sessions")
            if not receipt or "version" not in receipt:
                raise RuntimeError("No known owned version; no deletion performed")
            if receipt.get("status") == "cleaned":
                print("PASS: already cleaned")
                return
            try:
                checked_version(project, config, receipt)
            except ResourceNotFoundError:
                print("Recorded version already absent")
            else:
                project.agents.delete_version(config["agent_name"], receipt["version"], force=True)
            receipt["status"] = "cleaned"
            save(state, receipt)
            print("PASS: owned version deleted; no parent DELETE issued. Other versions and shared resources were not targeted; the last-version deletion can make the parent disappear.")


def main():
    # Serialize receipt writers. Uncertain creates remain blocked by the receipt.
    args = parse_args()
    state = private_path(args.state)
    state.parent.mkdir(parents=True, exist_ok=True)
    lock = state.with_suffix(".lock")
    try:
        lock.touch(exist_ok=False)
    except FileExistsError:
        raise RuntimeError("Another lifecycle operation holds the receipt lock; do not remove a live process's lock") from None
    try:
        run(args)
    finally:
        lock.unlink()


if __name__ == "__main__":
    try:
        main()
    except HttpResponseError as error:
        request_id = error.response.headers.get("x-ms-request-id") or error.response.headers.get("apim-request-id") if error.response else None
        code = getattr(error.error, "code", None)
        print(f"FAIL: HTTP {error.status_code}; code={code}; correlation={request_id}; inspect the retained receipt and Foundry diagnostics", file=sys.stderr)
        sys.exit(1)
    except (ValueError, RuntimeError, TimeoutError, OSError, subprocess.SubprocessError) as error:
        print("FAIL:", error, file=sys.stderr)
        sys.exit(1)
