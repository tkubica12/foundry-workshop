"""Repeatable lifecycle automation for the Chapter 2 teacher demonstration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

import httpx
from openai import RateLimitError
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentEndpointConfig,
    CodeConfiguration,
    FixedRatioVersionSelectionRule,
    HostedAgentDefinition,
    MemoryItemKind,
    MemorySearchOptions,
    MemorySearchPreviewTool,
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
    PromptAgentDefinition,
    ProtocolConfiguration,
    ProtocolVersionRecord,
    ResponsesProtocolConfiguration,
    VersionSelector,
)
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import AzureCliCredential

DEMO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DEMO_ROOT.parents[2]
AGENT_ROOT = DEMO_ROOT / "agent"
STATE_ROOT = REPO_ROOT / ".workshop" / "chapter-2"
STATE_PATH = STATE_ROOT / "state.json"
sys.path.insert(0, str(DEMO_ROOT / "harness"))
import contract as triage_contract

PROMPT_AGENT_NAME = "foundry-chapter2-prompt"
HOSTED_AGENT_NAME = "foundry-chapter2-langgraph"
MEMORY_AGENT_NAME = "foundry-chapter2-memory"
MEMORY_STORE_NAME = "foundry-chapter2-memory"
OWNER_METADATA = "foundry-workshop-chapter-2"
PROMPT_INSTRUCTIONS = """
You triage synthetic retail stock exceptions for an operations team.
Never provide medical advice, recommend substitutions, or claim access to live systems.
State the available stock and the shortfall explicitly using those words and digits.
Return concise operational guidance with exactly these headings: PRIORITY, NEXT ACTION,
ESCALATE WHEN.
""".strip()
STOCK_EXCEPTION = (
    "Synthetic store STORE-042 has 8 units on hand, 3 reserved units, and forecast "
    "demand of 14 units before the next planned delivery. Triage the exception."
)
FOLLOW_UP = "What shortfall did you use, and what single action should happen first?"
MEMORY_SCOPE = "chapter2-teacher"
MEMORY_ISOLATED_SCOPE = "chapter2-isolated-user"
MEMORY_MAX_OUTPUT_TOKENS = 200
MEMORY_FACT = (
    "For future synthetic stock reviews, remember that my preferred escalation "
    "channel is the GREEN-742 queue."
)
MEMORY_DISCUSSION_START = (
    "Open a synthetic review for incident STOCK-318. The expected count was 20 units, "
    "but the initial shelf count found 12. A delivery is due tomorrow."
)
MEMORY_DISCUSSION_CLOSE = (
    "Close the STOCK-318 discussion: a manual recount confirmed 18 units, so we decided "
    "that no transfer is required and the next delivery should be monitored."
)
MEMORY_RECALL_QUESTION = (
    "This is a new conversation. Which escalation channel do I prefer?"
)
MEMORY_SUMMARY_SEARCH_QUERY = (
    "What did we conclude in the prior synthetic stock incident that began with "
    "20 expected units and 12 on the shelf? Include its identifier and transfer decision."
)
MEMORY_INSTRUCTIONS = """
You assist with synthetic retail stock operations. Use persistent memory only for
non-sensitive user preferences. Never infer or store clinical, personal, credential,
financial, or live-system data. If a preference is unknown, say that it is unknown.
""".strip()
REQUIRED_PLATFORM_OUTPUTS = {
    "teacher_application_insights_id",
    "teacher_foundry_id",
    "teacher_log_analytics_workspace_id",
    "teacher_model_reference",
    "teacher_project_endpoint",
    "teacher_project_id",
}


class DemoError(RuntimeError):
    """A failure with an actionable operator message."""


@dataclass(frozen=True)
class PlatformContract:
    subscription_id: str
    tenant_id: str
    project_endpoint: str
    project_id: str
    foundry_id: str
    model_reference: str
    memory_chat_model: str | None
    memory_embedding_model: str | None
    application_insights_id: str
    log_analytics_workspace_id: str


def _executable_command(command: list[str]) -> tuple[list[str], bool]:
    executable = shutil.which(command[0])
    if executable is None:
        return command, False
    requires_shell = os.name == "nt" and Path(executable).suffix.lower() in {".bat", ".cmd"}
    return [executable, *command[1:]], requires_shell


def _run_json(command: list[str], *, cwd: Path | None = None, timeout: int = 120) -> Any:
    executable_command, requires_shell = _executable_command(command)
    env = os.environ.copy()
    if cwd is not None and command[0] == "uv":
        env.pop("VIRTUAL_ENV", None)
    try:
        completed = subprocess.run(
            executable_command,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=requires_shell,
        )
    except FileNotFoundError as error:
        raise DemoError(f"required command is unavailable: {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise DemoError(f"command timed out after {timeout}s: {' '.join(command)}") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        raise DemoError(f"command failed: {' '.join(command)}\n{detail}") from error
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise DemoError(f"command returned invalid JSON: {' '.join(command)}") from error


def parse_contract(payload: Mapping[str, Any]) -> PlatformContract:
    outputs = payload.get("platform_outputs")
    if not isinstance(outputs, Mapping):
        raise DemoError("lab status does not contain platform_outputs")
    missing = sorted(REQUIRED_PLATFORM_OUTPUTS - outputs.keys())
    if missing:
        raise DemoError(f"lab platform contract is missing: {', '.join(missing)}")

    values = {key: _required_string(outputs, key) for key in sorted(REQUIRED_PLATFORM_OUTPUTS)}
    tenant_id = _required_string(payload, "tenant_id")
    if not re.fullmatch(r"[A-Za-z0-9.-]+", tenant_id):
        raise DemoError("tenant_id must be a tenant identifier or domain")
    project_id = values["teacher_project_id"]
    resource_types = {
        "teacher_project_id": r"Microsoft\.CognitiveServices/accounts/([^/]+)/projects/([^/]+)",
        "teacher_foundry_id": r"Microsoft\.CognitiveServices/accounts/([^/]+)",
        "teacher_application_insights_id": r"Microsoft\.Insights/components/([^/]+)",
        "teacher_log_analytics_workspace_id": r"Microsoft\.OperationalInsights/workspaces/([^/]+)",
    }
    resource_parts: dict[str, re.Match[str]] = {}
    for field, suffix in resource_types.items():
        value = values[field]
        match = re.fullmatch(
            r"/subscriptions/([^/]+)/resourceGroups/([^/]+)/providers/" + suffix,
            value, re.IGNORECASE,
        )
        if not match or any(not re.fullmatch(r"[A-Za-z0-9_.()-]+", part) for part in match.groups()):
            raise DemoError(f"{field} must be a full Azure resource ID of the expected resource type")
        resource_parts[field] = match
    subscription_id = resource_parts["teacher_project_id"].group(1)
    for field, match in resource_parts.items():
        if match.group(1).lower() != subscription_id.lower():
            raise DemoError(f"{field} must belong to the teacher project subscription")
    if project_id.rsplit("/projects/", 1)[0].lower() != values["teacher_foundry_id"].lower():
        raise DemoError("teacher_foundry_id must be the parent account of teacher_project_id")
    endpoint = values["teacher_project_endpoint"]
    try:
        parsed = urlsplit(endpoint)
        valid_endpoint = (
            parsed.scheme == "https" and bool(parsed.hostname)
            and re.fullmatch(r"[A-Za-z0-9.-]+", parsed.hostname) is not None
            and parsed.username is None and parsed.password is None
            and not parsed.query and not parsed.fragment
            and parsed.port in (None, 443)
            and parsed.path.rstrip("/") == "/api/projects/" + resource_parts["teacher_project_id"].group(4)
            and "\\" not in endpoint
        )
    except ValueError:
        valid_endpoint = False
    if not valid_endpoint:
        raise DemoError("teacher_project_endpoint must be a credential-free HTTPS project URL matching teacher_project_id")
    if any(character.isspace() for character in values["teacher_model_reference"]):
        raise DemoError("teacher_model_reference must be a model reference without whitespace")

    return PlatformContract(
        subscription_id=subscription_id,
        tenant_id=tenant_id,
        project_endpoint=endpoint.rstrip("/"),
        project_id=project_id,
        foundry_id=values["teacher_foundry_id"],
        model_reference=values["teacher_model_reference"],
        memory_chat_model=_optional_string(
            outputs.get("teacher_memory_chat_model")
            or outputs.get("teacher_memory_chat_deployment_name")
        ),
        memory_embedding_model=_optional_string(
            outputs.get("teacher_memory_embedding_model")
            or outputs.get("teacher_memory_embedding_deployment_name")
        ),
        application_insights_id=values["teacher_application_insights_id"],
        log_analytics_workspace_id=values["teacher_log_analytics_workspace_id"],
    )


def _required_string(values: Mapping[str, Any], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip() or value != value.strip() or any(ord(c) < 32 for c in value):
        raise DemoError(f"{key} must be a nonempty string without surrounding whitespace or control characters")
    return value


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def load_contract(lab_repo: Path, prefix: str) -> PlatformContract:
    payload = _run_json(
        ["uv", "run", "labctl", "status", "--prefix", prefix],
        cwd=lab_repo,
        timeout=180,
    )
    if "tenant_id" not in payload:
        instance_path = lab_repo / ".lab" / "instances" / prefix / "instance.yaml"
        if not instance_path.is_file():
            raise DemoError(f"resolved lab instance is missing: {instance_path}")
        for line in instance_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("tenant_id:"):
                payload["tenant_id"] = line.split(":", 1)[1].strip()
                break
    return parse_contract(payload)


def credential_for(contract: PlatformContract) -> AzureCliCredential:
    return AzureCliCredential(tenant_id=contract.tenant_id, process_timeout=120)


def project_client(contract: PlatformContract) -> AIProjectClient:
    return AIProjectClient(
        endpoint=contract.project_endpoint,
        credential=credential_for(contract),
        allow_preview=True,
    )


def fingerprint_text(*values: str) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def create_source_archive(source_root: Path = AGENT_ROOT) -> bytes:
    files = [source_root / "main.py", source_root / "requirements.txt"]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise DemoError(f"agent source is incomplete: {', '.join(missing)}")

    with tempfile.SpooledTemporaryFile() as stream:
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
        stream.seek(0)
        return stream.read()


def _version_values(version: Any) -> Mapping[str, Any]:
    return version if isinstance(version, Mapping) else {}


def _version_metadata(version: Any) -> Mapping[str, str]:
    metadata = _version_values(version).get("metadata")
    return metadata if isinstance(metadata, Mapping) else {}


def _list_agent_versions(project: AIProjectClient, agent_name: str) -> list[Any]:
    try:
        return list(project.agents.list_versions(agent_name, include_drafts=True))
    except ResourceNotFoundError:
        return []


def _assert_agent_deployment_owned(project: AIProjectClient, agent_name: str) -> None:
    versions = _list_agent_versions(project, agent_name)
    if any(
        _version_metadata(version).get("workshop_owner") != OWNER_METADATA
        for version in versions
    ):
        raise DemoError(f"refusing to deploy or route unowned agent {agent_name}")
    try:
        project.agents.get(agent_name)
    except ResourceNotFoundError:
        return
    if not versions:
        raise DemoError(f"refusing to deploy or route existing empty agent {agent_name}")


def _agent_identity(agent: Any) -> str:
    values = agent if isinstance(agent, Mapping) else agent.as_dict()
    identity = values.get("instance_identity")
    principal_id = identity.get("principal_id") if isinstance(identity, Mapping) else None
    if not isinstance(principal_id, str) or not principal_id:
        raise DemoError("agent identity is missing; destructive ownership is unproven")
    return principal_id


def _validated_deletion_identities() -> dict[str, str]:
    values = _load_state().get("validated_agent_deletions")
    if not isinstance(values, Mapping):
        return {}
    return {
        str(name): str(identity)
        for name, identity in values.items()
        if isinstance(name, str) and isinstance(identity, str)
    }


def _agent_delete_candidate(
    project: AIProjectClient,
    agent_name: str,
    *,
    operation: str,
) -> tuple[list[Any], str | None]:
    try:
        versions = list(
            project.agents.list_versions(agent_name, include_drafts=True)
        )
    except ResourceNotFoundError:
        return [], None
    foreign = [
        str(version.version)
        for version in versions
        if _version_metadata(version).get("workshop_owner") != OWNER_METADATA
    ]
    if foreign:
        raise DemoError(
            f"refusing to {operation} {agent_name}; unowned versions: "
            f"{', '.join(foreign)}"
        )
    try:
        identity = _agent_identity(project.agents.get(agent_name))
    except ResourceNotFoundError:
        return [], None
    if not versions and _validated_deletion_identities().get(agent_name) != identity:
        raise DemoError(
            f"refusing to {operation} {agent_name}; the existing agent has no versions "
            "with workshop ownership metadata or a matching validated deletion identity"
        )
    return versions, identity


def _find_reusable_version(
    project: AIProjectClient,
    agent_name: str,
    fingerprint: str,
    *,
    resume_pending: bool = False,
    timeout_seconds: int = 900,
) -> Any | None:
    try:
        latest = next(
            iter(
                project.agents.list_versions(
                    agent_name,
                    include_drafts=False,
                    order="desc",
                    limit=1,
                )
            ),
            None,
        )
    except ResourceNotFoundError:
        latest = None
    if latest is None:
        return None
    metadata = _version_metadata(latest)
    status = str(_version_values(latest).get("status", "")).lower()
    if (
        metadata.get("workshop_owner") == OWNER_METADATA
        and metadata.get("content_sha256") == fingerprint
    ):
        if status == "active":
            return latest
        if resume_pending and status in {"pending", "provisioning", "creating", "updating"}:
            return _wait_for_active(project, agent_name, str(latest.version), timeout_seconds)
    return None


def _wait_for_active(
    project: AIProjectClient,
    agent_name: str,
    version: str,
    timeout_seconds: int,
) -> Any:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        details = project.agents.get_version(agent_name, version)
        values = _version_values(details)
        status = str(values.get("status", "")).lower()
        print(f"Hosted version {version}: {status or 'unknown'}")
        if status == "active":
            return details
        if status == "failed":
            raise DemoError(f"hosted version failed: {values.get('error', values)}")
        time.sleep(10)
    raise DemoError(f"hosted version {version} did not become active within {timeout_seconds}s")


def _route_hosted_version(project: AIProjectClient, version: str) -> None:
    _assert_agent_deployment_owned(project, HOSTED_AGENT_NAME)
    project.agents.update_details(
        agent_name=HOSTED_AGENT_NAME,
        agent_endpoint=AgentEndpointConfig(
            version_selector=VersionSelector(
                version_selection_rules=[
                    FixedRatioVersionSelectionRule(
                        agent_version=version,
                        traffic_percentage=100,
                    )
                ]
            ),
            protocol_configuration=ProtocolConfiguration(
                responses=ResponsesProtocolConfiguration()
            ),
        ),
    )


def ensure_prompt_agent(contract: PlatformContract, *, new_version: bool = False) -> str:
    fingerprint = fingerprint_text(contract.model_reference, PROMPT_INSTRUCTIONS)
    with project_client(contract) as project:
        _assert_agent_deployment_owned(project, PROMPT_AGENT_NAME)
        reusable = None if new_version else _find_reusable_version(
            project, PROMPT_AGENT_NAME, fingerprint
        )
        if reusable is not None:
            version = str(reusable.version)
            print(f"Reusing prompt agent version {version}")
            return version
        created = project.agents.create_version(
            agent_name=PROMPT_AGENT_NAME,
            description="Chapter 2 prompt-agent baseline.",
            metadata={
                "workshop_owner": OWNER_METADATA,
                "content_sha256": fingerprint,
            },
            definition=PromptAgentDefinition(
                model=contract.model_reference,
                instructions=PROMPT_INSTRUCTIONS,
            ),
        )
        print(f"Created prompt agent version {created.version}")
        return str(created.version)


def _memory_models(contract: PlatformContract) -> tuple[str, str]:
    if not contract.memory_chat_model or not contract.memory_embedding_model:
        raise DemoError(
            "teacher Memory models are absent from the platform contract; "
            "deploy the lab environment Memory prerequisites first"
        )
    return contract.memory_chat_model, contract.memory_embedding_model


def _memory_store_options() -> MemoryStoreDefaultOptions:
    return MemoryStoreDefaultOptions(
        user_profile_enabled=True,
        user_profile_details=(
            "Store only explicit non-sensitive synthetic workshop preferences, such "
            "as a preferred queue. Do not infer a role or profile from incident work. "
            "Exclude clinical, personal, credential, financial, precise "
            "location, and live-system data."
        ),
        chat_summary_enabled=True,
        procedural_memory_enabled=False,
        default_ttl_seconds=timedelta(days=1),
    )


def _memory_store_options_match(options: Any) -> bool:
    return callable(getattr(options, "as_dict", None)) and (
        options.as_dict() == _memory_store_options().as_dict()
    )


def ensure_memory_store(contract: PlatformContract) -> str:
    chat_model, embedding_model = _memory_models(contract)
    with project_client(contract) as project:
        try:
            existing = project.beta.memory_stores.get(name=MEMORY_STORE_NAME)
        except ResourceNotFoundError:
            existing = None
        if existing is not None:
            metadata = getattr(existing, "metadata", None)
            if not isinstance(metadata, Mapping) or metadata.get(
                "workshop_owner"
            ) != OWNER_METADATA:
                raise DemoError(
                    f"refusing to reuse unowned memory store {MEMORY_STORE_NAME}"
                )
            definition = getattr(existing, "definition", None)
            if (
                getattr(definition, "chat_model", None) != chat_model
                or getattr(definition, "embedding_model", None) != embedding_model
            ):
                raise DemoError(
                    "owned memory store model configuration changed; run cleanup "
                    "before preparing the new platform contract"
                )
            options = getattr(definition, "options", None)
            if not _memory_store_options_match(options):
                raise DemoError(
                    "owned memory store extraction or retention configuration changed; "
                    "run memory-reset before prepare"
                )
            print(f"Reusing memory store {MEMORY_STORE_NAME}")
            return MEMORY_STORE_NAME

        created = project.beta.memory_stores.create(
            name=MEMORY_STORE_NAME,
            description="Chapter 2 synthetic cross-conversation recall.",
            metadata={"workshop_owner": OWNER_METADATA},
            definition=MemoryStoreDefaultDefinition(
                chat_model=chat_model,
                embedding_model=embedding_model,
                options=_memory_store_options(),
            ),
        )
        print(f"Created memory store {created.name}")
        return str(created.name)


def ensure_memory_agent(
    contract: PlatformContract,
    *,
    new_version: bool = False,
) -> str:
    chat_model, embedding_model = _memory_models(contract)
    fingerprint = fingerprint_text(
        chat_model,
        embedding_model,
        MEMORY_STORE_NAME,
        MEMORY_INSTRUCTIONS,
    )
    with project_client(contract) as project:
        _assert_agent_deployment_owned(project, MEMORY_AGENT_NAME)
        ensure_memory_store(contract)
        reusable = None if new_version else _find_reusable_version(
            project, MEMORY_AGENT_NAME, fingerprint
        )
        if reusable is not None:
            version = str(reusable.version)
            print(f"Reusing memory agent version {version}")
            return version
        created = project.agents.create_version(
            agent_name=MEMORY_AGENT_NAME,
            description="Chapter 2 persistent Memory comparison.",
            metadata={
                "workshop_owner": OWNER_METADATA,
                "content_sha256": fingerprint,
            },
            definition=PromptAgentDefinition(
                model=chat_model,
                instructions=MEMORY_INSTRUCTIONS,
                tools=[
                    MemorySearchPreviewTool(
                        memory_store_name=MEMORY_STORE_NAME,
                        scope="{{$userId}}",
                        update_delay=1,
                    )
                ],
            ),
        )
        print(f"Created memory agent version {created.version}")
        return str(created.version)


def _clear_memory_scope(
    project: AIProjectClient,
    scope: str,
    *,
    timeout_seconds: int = 60,
) -> None:
    try:
        project.beta.memory_stores.delete_scope(
            name=MEMORY_STORE_NAME,
            scope=scope,
        )
    except ResourceNotFoundError:
        return
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        memories = list(
            project.beta.memory_stores.list_memories(
                name=MEMORY_STORE_NAME,
                scope=scope,
            )
        )
        if not memories:
            return
        time.sleep(2)
    raise DemoError(
        f"Memory scope {scope} did not clear within {timeout_seconds}s"
    )


def _memory_kind(memory: Any) -> str:
    kind = getattr(memory, "kind", "")
    return str(getattr(kind, "value", kind))


def _wait_for_memory_kinds(
    project: AIProjectClient,
    *,
    scope: str,
    timeout_seconds: int,
    required_kinds: set[str],
) -> list[Any]:
    deadline = time.monotonic() + timeout_seconds
    observed_kinds: set[str] = set()
    while time.monotonic() < deadline:
        memories = list(
            project.beta.memory_stores.list_memories(
                name=MEMORY_STORE_NAME,
                scope=scope,
            )
        )
        observed_kinds = {_memory_kind(memory) for memory in memories}
        if required_kinds <= observed_kinds:
            return memories
        time.sleep(2)
    raise DemoError(
        f"persistent Memory did not extract {sorted(required_kinds)} for scope {scope} "
        f"within {timeout_seconds}s; observed {sorted(observed_kinds)}"
    )


def _wait_for_contextual_summary(
    project: AIProjectClient,
    *,
    scope: str,
    query: str,
    timeout_seconds: int,
) -> tuple[list[Any], str]:
    deadline = time.monotonic() + timeout_seconds
    observed_summaries: list[str] = []
    while time.monotonic() < deadline:
        memories = _search_contextual_memories(project, scope=scope, query=query)
        observed_summaries = [
            memory.content
            for memory in memories
            if _memory_kind(memory) == "chat_summary"
        ]
        matching = [
            content
            for content in observed_summaries
            if "STOCK-318" in content.upper() and "NO TRANSFER" in content.upper()
        ]
        if matching:
            return memories, matching[0]
        time.sleep(2)
    raise DemoError(
        "contextual chat summary search did not retrieve the STOCK-318 no-transfer "
        f"decision within {timeout_seconds}s; observed {len(observed_summaries)} summaries"
    )


def _search_contextual_memories(
    project: AIProjectClient,
    *,
    scope: str,
    query: str,
) -> list[Any]:
    result = project.beta.memory_stores.search_memories(
        name=MEMORY_STORE_NAME,
        scope=scope,
        items=[{"role": "user", "content": query, "type": "message"}],
        options=MemorySearchOptions(max_memories=10),
    )
    return [search_item.memory_item for search_item in result.memories]


def _search_static_memories(
    project: AIProjectClient,
    *,
    scope: str,
) -> list[Any]:
    result = project.beta.memory_stores.search_memories(
        name=MEMORY_STORE_NAME,
        scope=scope,
        options=MemorySearchOptions(max_memories=10),
    )
    return [search_item.memory_item for search_item in result.memories]


def _create_response_with_retry(
    openai: Any,
    *,
    attempts: int = 5,
    **kwargs: Any,
) -> Any:
    for attempt in range(attempts):
        try:
            return openai.responses.create(**kwargs)
        except RateLimitError as error:
            request_id = error.response.headers.get("x-request-id")
            if not request_id and isinstance(error.body, Mapping):
                additional = error.body.get("additionalInfo")
                if isinstance(additional, Mapping):
                    request_id = _optional_string(additional.get("request_id"))
            request_id = request_id or "unknown"
            if attempt == attempts - 1:
                raise DemoError(
                    "Memory model rate limit persisted after "
                    f"{attempts} attempts; request ID: {request_id}"
                ) from error
            retry_after_ms = error.response.headers.get("retry-after-ms")
            retry_after = error.response.headers.get("retry-after")
            try:
                if retry_after_ms:
                    service_delay = float(retry_after_ms) / 1000
                else:
                    service_delay = float(retry_after) if retry_after else 0
            except ValueError:
                service_delay = 0
            delay = min(max(service_delay, min(15 * (attempt + 1), 45)), 60)
            print(
                f"Memory model rate limited; retrying in {delay:g}s "
                f"(request ID: {request_id})"
            )
            time.sleep(delay)
    raise AssertionError("response retry loop exhausted unexpectedly")


def _create_memory_response(openai: Any, **kwargs: Any) -> Any:
    return _create_response_with_retry(
        openai,
        max_output_tokens=MEMORY_MAX_OUTPUT_TOKENS,
        **kwargs,
    )


def invoke_memory_showcase(
    contract: PlatformContract,
    *,
    timeout_seconds: int = 120,
    new_version: bool = False,
) -> dict[str, Any]:
    version = ensure_memory_agent(contract, new_version=new_version)
    with project_client(contract) as project:
        _clear_memory_scope(project, MEMORY_SCOPE)
        _clear_memory_scope(project, MEMORY_ISOLATED_SCOPE)
        openai = project.get_openai_client()
        reference = {
            "agent_reference": {
                "name": MEMORY_AGENT_NAME,
                "version": version,
                "type": "agent_reference",
            }
        }
        first_conversation = openai.conversations.create()
        try:
            profile_learned = _create_memory_response(
                openai,
                conversation=first_conversation.id,
                input=MEMORY_FACT,
                extra_body=reference,
                extra_headers={"x-memory-user-id": MEMORY_SCOPE},
            )
            discussion_started = _create_memory_response(
                openai,
                conversation=first_conversation.id,
                input=MEMORY_DISCUSSION_START,
                extra_body=reference,
                extra_headers={"x-memory-user-id": MEMORY_SCOPE},
            )
            discussion_closed = _create_memory_response(
                openai,
                conversation=first_conversation.id,
                input=MEMORY_DISCUSSION_CLOSE,
                extra_body=reference,
                extra_headers={"x-memory-user-id": MEMORY_SCOPE},
            )
            memories = _wait_for_memory_kinds(
                project,
                scope=MEMORY_SCOPE,
                timeout_seconds=timeout_seconds,
                required_kinds={"user_profile", "chat_summary"},
            )
        finally:
            openai.conversations.delete(first_conversation.id)

        _contextual_memories, chat_summary_text = _wait_for_contextual_summary(
            project,
            scope=MEMORY_SCOPE,
            query=MEMORY_SUMMARY_SEARCH_QUERY,
            timeout_seconds=timeout_seconds,
        )
        isolated_contextual_memories = _search_contextual_memories(
            project,
            scope=MEMORY_ISOLATED_SCOPE,
            query=MEMORY_SUMMARY_SEARCH_QUERY,
        )
        isolated_static_memories = _search_static_memories(
            project,
            scope=MEMORY_ISOLATED_SCOPE,
        )
        if isolated_contextual_memories or isolated_static_memories:
            raise DemoError(
                "persistent Memory crossed user scopes; isolated API searches returned "
                f"{len(isolated_static_memories)} static and "
                f"{len(isolated_contextual_memories)} contextual memories"
            )

        recall_conversation = openai.conversations.create()
        try:
            recalled = _create_memory_response(
                openai,
                conversation=recall_conversation.id,
                input=MEMORY_RECALL_QUESTION,
                extra_body=reference,
                extra_headers={"x-memory-user-id": MEMORY_SCOPE},
            )
        finally:
            openai.conversations.delete(recall_conversation.id)

        isolated_conversation = openai.conversations.create()
        try:
            isolated = _create_memory_response(
                openai,
                conversation=isolated_conversation.id,
                input=MEMORY_RECALL_QUESTION,
                extra_body=reference,
                extra_headers={"x-memory-user-id": MEMORY_ISOLATED_SCOPE},
            )
        finally:
            openai.conversations.delete(isolated_conversation.id)
            openai.close()

    recalled_text = recalled.output_text.strip()
    isolated_text = isolated.output_text.strip()
    recalled_upper = recalled_text.upper()
    isolated_upper = isolated_text.upper()
    if "GREEN-742" not in recalled_upper:
        raise DemoError(
            f"persistent Memory did not recall the GREEN-742 queue: {recalled_text}"
        )
    if "GREEN-742" in isolated_upper or "STOCK-318" in isolated_upper:
        raise DemoError(
            "persistent Memory crossed user scopes; isolated agent received a known "
            "profile or summary identifier"
        )
    result = {
        "profile_learned": profile_learned.output_text.strip(),
        "discussion_started": discussion_started.output_text.strip(),
        "discussion_closed": discussion_closed.output_text.strip(),
        "memory_items": len(memories),
        "memory_kinds": sorted({_memory_kind(memory) for memory in memories}),
        "profile_recalled_in_new_conversation": recalled_text,
        "chat_summary_recalled_contextually": chat_summary_text,
        "isolated_profile": isolated_text,
        "isolated_static_memory_items": len(isolated_static_memories),
        "isolated_chat_summary_items": len(isolated_contextual_memories),
    }
    _save_state(
        {
            "memory_showcase": result,
            "memory_validated_at": datetime.now(UTC).isoformat(),
        }
    )
    return result


def memory_fallback() -> dict[str, Any]:
    state = _load_state()
    result = state.get("memory_showcase")
    validated_at = state.get("memory_validated_at")
    if not isinstance(result, Mapping) or not isinstance(validated_at, str):
        raise DemoError(
            "no prevalidated Memory result exists; run prepare before delivery"
        )
    return {
        "prevalidated": True,
        "validated_at": validated_at,
        **result,
    }


def reset_memory_resources(contract: PlatformContract) -> dict[str, Any]:
    removed: dict[str, Any] = {"agent_versions": []}
    failures: list[dict[str, str]] = []
    with project_client(contract) as project:
        versions, agent_identity = _agent_delete_candidate(
            project,
            MEMORY_AGENT_NAME,
            operation="reset",
        )
        try:
            memory_store = project.beta.memory_stores.get(name=MEMORY_STORE_NAME)
        except ResourceNotFoundError:
            memory_store = None
        if memory_store is not None:
            metadata = getattr(memory_store, "metadata", None)
            if not isinstance(metadata, Mapping) or metadata.get(
                "workshop_owner"
            ) != OWNER_METADATA:
                raise DemoError(
                    f"refusing to reset unowned memory store {MEMORY_STORE_NAME}"
                )
        if agent_identity is not None:
            identities = _validated_deletion_identities()
            identities[MEMORY_AGENT_NAME] = agent_identity
            _save_state({"validated_agent_deletions": identities})

        for version in versions:
            version_number = str(version.version)
            try:
                project.agents.delete_version(
                    agent_name=MEMORY_AGENT_NAME,
                    agent_version=version_number,
                    force=True,
                )
                removed["agent_versions"].append(version_number)
            except ResourceNotFoundError:
                pass
            except HttpResponseError as error:
                failures.append(
                    {"resource": f"agent version {version_number}", "error": str(error)}
                )
        if not failures:
            try:
                project.agents.delete(MEMORY_AGENT_NAME)
                removed["agent"] = MEMORY_AGENT_NAME
            except ResourceNotFoundError:
                pass
            except HttpResponseError as error:
                failures.append(
                    {"resource": MEMORY_AGENT_NAME, "error": str(error)}
                )
        if memory_store is not None and not failures:
            try:
                project.beta.memory_stores.delete(name=MEMORY_STORE_NAME)
                removed["memory_store"] = MEMORY_STORE_NAME
            except ResourceNotFoundError:
                pass
            except HttpResponseError as error:
                failures.append(
                    {"resource": MEMORY_STORE_NAME, "error": str(error)}
                )
    if failures:
        raise DemoError(
            "memory reset incomplete; removed="
            f"{json.dumps(removed, sort_keys=True)}; "
            f"failed_or_retained={json.dumps(failures, sort_keys=True)}"
        )
    state = _load_state()
    state.pop("memory_showcase", None)
    state.pop("memory_validated_at", None)
    identities = state.get("validated_agent_deletions")
    if isinstance(identities, dict):
        identities.pop(MEMORY_AGENT_NAME, None)
        if not identities:
            state.pop("validated_agent_deletions", None)
    if state:
        STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    elif STATE_PATH.exists():
        STATE_PATH.unlink()
    return removed


def hosted_definition(contract: PlatformContract) -> HostedAgentDefinition:
    return HostedAgentDefinition(
        cpu="0.5",
        memory="1Gi",
        code_configuration=CodeConfiguration(
            runtime="python_3_13",
            entry_point=["python", "main.py"],
            dependency_resolution="remote_build",
        ),
        environment_variables={
            "AZURE_AI_MODEL_DEPLOYMENT_NAME": contract.model_reference,
            "FOUNDRY_PROJECT_ENDPOINT": contract.project_endpoint,
        },
        protocol_versions=[ProtocolVersionRecord(protocol="responses", version="2.0.0")],
    )


def hosted_fingerprint(source: bytes, definition: HostedAgentDefinition) -> str:
    return fingerprint_text(
        hashlib.sha256(source).hexdigest(),
        json.dumps(definition.as_dict(), sort_keys=True, separators=(",", ":")),
    )


def deploy_hosted_agent(
    contract: PlatformContract,
    *,
    new_version: bool = False,
    timeout_seconds: int = 900,
) -> str:
    source = create_source_archive()
    source_hash = hashlib.sha256(source).hexdigest()
    definition = hosted_definition(contract)
    fingerprint = hosted_fingerprint(source, definition)
    with project_client(contract) as project:
        _assert_agent_deployment_owned(project, HOSTED_AGENT_NAME)
        reusable = None if new_version else _find_reusable_version(
            project, HOSTED_AGENT_NAME, fingerprint,
            resume_pending=True, timeout_seconds=timeout_seconds,
        )
        if reusable is None:
            with tempfile.TemporaryDirectory(prefix="foundry-chapter2-") as directory:
                source_path = Path(directory) / "agent.zip"
                source_path.write_bytes(source)
                with source_path.open("rb") as code:
                    created = project.agents.create_version_from_code(
                        agent_name=HOSTED_AGENT_NAME,
                        description="Chapter 2 LangGraph source deployment.",
                        metadata={
                            "workshop_owner": OWNER_METADATA,
                            "content_sha256": fingerprint,
                        },
                        definition=definition,
                        code=code,
                        code_zip_sha256=source_hash,
                    )
            active = _wait_for_active(
                project,
                HOSTED_AGENT_NAME,
                str(created.version),
                timeout_seconds,
            )
        else:
            active = reusable
            print(f"Reusing hosted agent version {active.version}")
        version = str(active.version)
        _route_hosted_version(project, version)
        print(f"Routed {HOSTED_AGENT_NAME} to version {version}")
    _save_state(
        {
            "hosted_version": version,
            "source_sha256": source_hash,
            "deployment_sha256": fingerprint,
            "project_endpoint": contract.project_endpoint,
            "deployed_at": datetime.now(UTC).isoformat(),
        }
    )
    return version


def _conversation(
    project: AIProjectClient,
    *,
    agent_name: str,
    agent_version: str | None,
    first_input: str = STOCK_EXCEPTION,
) -> dict[str, Any]:
    if agent_version is None:
        openai = project.get_openai_client(agent_name=agent_name)
    else:
        openai = project.get_openai_client()
    conversation = openai.conversations.create()
    try:
        extra_body = None
        if agent_version is not None:
            extra_body = {
                "agent_reference": {
                    "name": agent_name,
                    "version": agent_version,
                    "type": "agent_reference",
                }
            }
        first = openai.responses.create(
            conversation=conversation.id,
            input=first_input,
            extra_body=extra_body,
            extra_headers={"traceparent": _traceparent(first_trace := uuid.uuid4().hex)},
        )
        second = openai.responses.create(
            conversation=conversation.id,
            input=FOLLOW_UP,
            extra_body=extra_body,
            extra_headers={"traceparent": _traceparent(second_trace := uuid.uuid4().hex)},
        )
        for response in (first, second):
            if response.status != "completed":
                raise DemoError(f"agent response {response.id} is {response.status}, not completed")
        return {
            "first": first.output_text.strip(), "follow_up": second.output_text.strip(),
            "first_output": first.model_dump().get("output", []),
            "response_ids": [first.id, second.id],
            "trace_ids": [first_trace, second_trace],
            "conversation_id": conversation.id,
        }
    finally:
        openai.conversations.delete(conversation.id)
        openai.close()


def _traceparent(trace_id: str) -> str:
    return f"00-{trace_id}-{uuid.uuid4().hex[:16]}-01"


def invoke_prompt_agent(contract: PlatformContract) -> dict[str, Any]:
    version = ensure_prompt_agent(contract)
    with project_client(contract) as project:
        return _conversation(
            project,
            agent_name=PROMPT_AGENT_NAME,
            agent_version=version,
        )


def _check_hosted_route(project: AIProjectClient, contract: PlatformContract) -> dict[str, str]:
    state = _load_state()
    fingerprint = hosted_fingerprint(create_source_archive(), hosted_definition(contract))
    if (
        state.get("project_endpoint") != contract.project_endpoint
        or state.get("deployment_sha256") != fingerprint
        or not state.get("hosted_version")
    ):
        raise DemoError("hosted source/configuration provenance is missing or changed; run prepare")
    version = str(state["hosted_version"])
    details = project.agents.get_version(HOSTED_AGENT_NAME, version)
    if (
        _version_metadata(details).get("content_sha256") != fingerprint
        or _version_metadata(details).get("workshop_owner") != OWNER_METADATA
        or _version_values(details).get("status") != "active"
    ):
        raise DemoError("hosted version is not the active owned source/configuration")
    agent = project.agents.get(HOSTED_AGENT_NAME)
    values = agent if isinstance(agent, Mapping) else agent.as_dict()
    rules = values.get("agent_endpoint", {}).get("version_selector", {}).get("version_selection_rules", [])
    if len(rules) != 1 or str(rules[0].get("agent_version")) != version or rules[0].get("traffic_percentage") != 100:
        raise DemoError("hosted endpoint is not routed exclusively to the intended version")
    return {"version": version, "deployment_sha256": fingerprint}


def invoke_hosted_agent(contract: PlatformContract) -> dict[str, Any]:
    with project_client(contract) as project:
        provenance = _check_hosted_route(project, contract)
        result = _conversation(
            project,
            agent_name=HOSTED_AGENT_NAME,
            agent_version=None,
        )
        if _check_hosted_route(project, contract) != provenance:
            raise DemoError("hosted endpoint changed during the showcase")
        result["provenance"] = provenance
        return result


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def invoke_local_agent(contract: PlatformContract, *, timeout_seconds: int = 180) -> dict[str, Any]:
    port = _available_port()
    env = os.environ.copy()
    env.update(
        {
            "AZURE_AI_MODEL_DEPLOYMENT_NAME": contract.model_reference,
            "FOUNDRY_PROJECT_ENDPOINT": contract.project_endpoint,
            "PORT": str(port),
        }
    )
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = STATE_ROOT / "local-agent.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, str(AGENT_ROOT / "main.py")],
            cwd=AGENT_ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.monotonic() + timeout_seconds
            with httpx.Client(timeout=90) as client:
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise DemoError(
                            f"local agent exited with {process.returncode}; see {log_path}"
                        )
                    try:
                        readiness = client.get(f"http://127.0.0.1:{port}/readiness")
                        if readiness.is_success:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(2)
                else:
                    raise DemoError(
                        f"local agent was not ready within {timeout_seconds}s; see {log_path}"
                    )
                response = client.post(
                    f"http://127.0.0.1:{port}/responses",
                    json={"input": STOCK_EXCEPTION, "stream": False},
                )
                response.raise_for_status()
                payload = response.json()
                text = _response_text(payload)
                if not text:
                    raise DemoError(f"local response contained no output text: {payload}")
                response_id = payload.get("id")
                if not response_id or payload.get("status") != "completed":
                    raise DemoError("local first response did not complete with a response ID")
                follow_up = client.post(
                    f"http://127.0.0.1:{port}/responses",
                    json={"input": FOLLOW_UP, "previous_response_id": response_id, "stream": False},
                )
                follow_up.raise_for_status()
                second = follow_up.json()
                if second.get("status") != "completed":
                    raise DemoError("local follow-up did not complete")
                result = {
                    "first": text, "follow_up": _response_text(second),
                    "first_output": payload.get("output", []),
                    "response_ids": [response_id, second.get("id")],
                    "source_sha256": hashlib.sha256(create_source_archive()).hexdigest(),
                }
                assert_showcase_response("local agent", result, require_tool=True)
                return result
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


def _response_text(payload: Mapping[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str):
        return direct.strip()
    chunks: list[str] = []
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, Mapping):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, Mapping) and isinstance(block.get("text"), str):
                    chunks.append(block["text"])
    return "".join(chunks).strip()


def assert_showcase_response(
    label: str, responses: Mapping[str, Any], *, require_tool: bool = False
) -> None:
    for turn in ("first", "follow_up"):
        text = responses.get(turn)
        if not isinstance(text, str) or not text:
            raise DemoError(f"{label} {turn} response is empty")
        result = triage_contract.score(text)
        failures = [
            item for item in result.failures
            if turn == "first" or item.key in {"shortfall", "clinical", "live_system"}
        ]
        if failures:
            raise DemoError(f"{label} {turn}: " + "; ".join(item.detail for item in failures))
    if not re.search(
        r"\b(?:first|next action)\b.{0,80}\b(?:raise|request|confirm|check|review|escalate|contact|arrange|replenish)\w*",
        responses["follow_up"], re.IGNORECASE | re.DOTALL,
    ):
        raise DemoError(f"{label} follow-up lacks a first operational action")
    if require_tool:
        assert_shortfall_tool(responses.get("first_output", []))


def assert_shortfall_tool(output: Any) -> None:
    if not isinstance(output, list):
        raise DemoError("deterministic tool evidence is missing")
    for call in output:
        if not isinstance(call, Mapping) or call.get("type") != "function_call" or call.get("name") != "calculate_shortfall":
            continue
        try:
            arguments = json.loads(call.get("arguments", ""))
        except (TypeError, json.JSONDecodeError):
            continue
        if arguments != {"current_stock": 8, "reserved_stock": 3, "forecast_demand": 14}:
            continue
        for result in output:
            if not isinstance(result, Mapping) or result.get("type") != "function_call_output":
                continue
            if not call.get("call_id") or result.get("call_id") != call["call_id"]:
                continue
            try:
                value = json.loads(result.get("output", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if value == {"available_stock": 5, "forecast_demand": 14, "shortfall": 9}:
                return
    raise DemoError("missing matching calculate_shortfall call and deterministic 5/9 tool result")


def verify_trace(
    contract: PlatformContract,
    *,
    started_at: datetime,
    trace_ids: list[str],
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    if not trace_ids or any(not re.fullmatch(r"[0-9a-f]{32}", item) for item in trace_ids):
        raise DemoError("exact invocation trace IDs are required")
    credential = credential_for(contract)
    management_token = credential.get_token("https://management.azure.com/.default").token
    workspace_response = httpx.get(
        f"https://management.azure.com{contract.log_analytics_workspace_id}",
        params={"api-version": "2023-09-01"},
        headers={"Authorization": f"Bearer {management_token}"},
        timeout=30,
    )
    workspace_response.raise_for_status()
    customer_id = workspace_response.json().get("properties", {}).get("customerId")
    if not customer_id:
        raise DemoError("teacher Log Analytics workspace has no customer ID")

    logs_token = credential.get_token("https://api.loganalytics.io/.default").token
    start = started_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    query = (
        "AppDependencies "
        f"| where TimeGenerated >= datetime({start}) "
        f'| where Name startswith "invoke_agent {HOSTED_AGENT_NAME}" '
        f"| where OperationId in ({', '.join(json.dumps(item) for item in trace_ids)}) "
        "| summarize records=count() by OperationId"
    )
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = httpx.post(
            f"https://api.loganalytics.io/v1/workspaces/{customer_id}/query",
            headers={"Authorization": f"Bearer {logs_token}"},
            json={"query": query},
            timeout=30,
        )
        response.raise_for_status()
        tables = response.json().get("tables", [])
        rows = tables[0].get("rows", []) if tables else []
        found = {
            row[0]: row[1] for row in rows
            if len(row) == 2 and row[0] in trace_ids and isinstance(row[1], int) and row[1] > 0
        }
        if all(trace_id in found for trace_id in trace_ids):
            return {"operation_ids": trace_ids, "records": sum(found.values())}
        time.sleep(15)
    raise DemoError(f"exact teacher traces {trace_ids} did not arrive within {timeout_seconds}s")


def cleanup(contract: PlatformContract) -> dict[str, Any]:
    removed: dict[str, Any] = {}
    failures: dict[str, list[dict[str, str]]] = {}
    with project_client(contract) as project:
        agent_names = (
            HOSTED_AGENT_NAME,
            PROMPT_AGENT_NAME,
            MEMORY_AGENT_NAME,
        )
        delete_candidates = {
            agent_name: _agent_delete_candidate(
                project, agent_name, operation="clean"
            )
            for agent_name in agent_names
        }
        versions_by_agent = {
            agent_name: candidate[0]
            for agent_name, candidate in delete_candidates.items()
        }
        try:
            memory_store = project.beta.memory_stores.get(name=MEMORY_STORE_NAME)
        except ResourceNotFoundError:
            memory_store = None

        if memory_store is not None:
            metadata = getattr(memory_store, "metadata", None)
            if not isinstance(metadata, Mapping) or metadata.get(
                "workshop_owner"
            ) != OWNER_METADATA:
                raise DemoError(
                    f"refusing to clean unowned memory store {MEMORY_STORE_NAME}"
                )
        identities = _validated_deletion_identities()
        identities.update(
            {
                agent_name: identity
                for agent_name, (_, identity) in delete_candidates.items()
                if identity is not None
            }
        )
        if identities:
            _save_state({"validated_agent_deletions": identities})

        for agent_name, versions in versions_by_agent.items():
            removed[agent_name] = []
            for version in versions:
                version_number = str(version.version)
                try:
                    project.agents.delete_version(
                        agent_name=agent_name,
                        agent_version=version_number,
                        force=True,
                    )
                    removed[agent_name].append(version_number)
                except ResourceNotFoundError:
                    pass
                except HttpResponseError as error:
                    failures.setdefault(agent_name, []).append(
                        {"version": version_number, "error": str(error)}
                    )
            try:
                project.agents.delete(agent_name)
            except ResourceNotFoundError:
                pass
            except HttpResponseError as error:
                failures.setdefault(agent_name, []).append(
                    {"resource": "agent", "error": str(error)}
                )
        if memory_store is not None:
            try:
                project.beta.memory_stores.delete(name=MEMORY_STORE_NAME)
                removed["memory_store"] = MEMORY_STORE_NAME
            except ResourceNotFoundError:
                pass
            except HttpResponseError as error:
                failures["memory_store"] = [
                    {"resource": MEMORY_STORE_NAME, "error": str(error)}
                ]
    if failures:
        raise DemoError(
            "cleanup incomplete; removed="
            f"{json.dumps(removed, sort_keys=True)}; "
            f"failed_or_retained={json.dumps(failures, sort_keys=True)}; "
            f"state retained at {STATE_PATH}"
        )
    if STATE_PATH.exists():
        STATE_PATH.unlink()
    return removed


def preflight(contract: PlatformContract) -> dict[str, Any]:
    if sys.version_info < (3, 13):
        raise DemoError("Python 3.13 or later is required")
    if shutil.which("az") is None:
        raise DemoError("Azure CLI is not installed")
    account = _run_json(["az", "account", "show", "--output", "json"], timeout=120)
    if str(account.get("id", "")).lower() != contract.subscription_id.lower():
        raise DemoError(
            f"Azure CLI subscription is {account.get('id')}; "
            f"expected {contract.subscription_id}"
        )
    if str(account.get("tenantId", "")).lower() != contract.tenant_id.lower():
        raise DemoError(
            f"Azure CLI tenant is {account.get('tenantId')}; expected {contract.tenant_id}"
        )
    credential_for(contract).get_token("https://ai.azure.com/.default")
    with project_client(contract) as project:
        list(project.agents.list(limit=1))
    return {
        "azure_account": account.get("name"),
        "project_endpoint": contract.project_endpoint,
        "model_reference": contract.model_reference,
        "memory_chat_model": contract.memory_chat_model,
        "memory_embedding_model": contract.memory_embedding_model,
        "python": sys.version.split()[0],
    }


def _save_state(values: Mapping[str, Any]) -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    current = _load_state()
    current.update(values)
    STATE_PATH.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {}
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise DemoError(f"invalid demo state: {STATE_PATH}") from error
    return value if isinstance(value, dict) else {}


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _contract_for(args: argparse.Namespace) -> PlatformContract:
    if args.contract_file:
        try:
            payload = json.loads(Path(args.contract_file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DemoError("cannot read the explicit teacher contract JSON") from error
        if not isinstance(payload, Mapping):
            raise DemoError("teacher contract must be a JSON object")
        return parse_contract(payload)
    if not args.resolve_platform:
        raise DemoError(
            "provide --contract-file with the operator's nonsecret teacher contract. "
            "The legacy --resolve-platform resolver can read secrets and mutate external setup; "
            "it requires separately authorized platform access."
        )
    return load_contract(Path(args.lab_repo).resolve(), args.prefix)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "contract",
            "preflight",
            "prepare",
            "prompt",
            "memory",
            "memory-fallback",
            "memory-reset",
            "local",
            "deploy",
            "verify",
            "showcase",
            "cleanup",
        ],
    )
    parser.add_argument(
        "--lab-repo",
        default=os.environ.get("WORKSHOP_PLATFORM_REPO", str(REPO_ROOT / ".workshop" / "platform")),
    )
    parser.add_argument("--prefix", default="workshop")
    contract_source = parser.add_mutually_exclusive_group()
    contract_source.add_argument("--contract-file", help="explicit nonsecret teacher contract JSON")
    contract_source.add_argument(
        "--resolve-platform", action="store_true",
        help="explicitly authorize the legacy external labctl resolver and its setup side effects",
    )
    parser.add_argument("--new-version", action="store_true")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "memory-fallback":
            _print_json(memory_fallback())
            return 0
        contract = _contract_for(args)
        if args.command == "contract":
            _print_json(asdict(contract))
        elif args.command == "preflight":
            _print_json(preflight(contract))
        elif args.command == "prompt":
            _print_json(invoke_prompt_agent(contract))
        elif args.command == "memory":
            _print_json(
                invoke_memory_showcase(
                    contract,
                    timeout_seconds=args.timeout,
                    new_version=args.new_version,
                )
            )
        elif args.command == "memory-reset":
            _print_json(reset_memory_resources(contract))
        elif args.command == "local":
            _print_json({"local_agent": invoke_local_agent(contract)})
        elif args.command == "deploy":
            version = deploy_hosted_agent(
                contract,
                new_version=args.new_version,
                timeout_seconds=args.timeout,
            )
            _print_json({"agent": HOSTED_AGENT_NAME, "version": version})
        elif args.command == "prepare":
            checks = preflight(contract)
            prompt_version = ensure_prompt_agent(contract)
            hosted_version = deploy_hosted_agent(
                contract,
                new_version=args.new_version,
                timeout_seconds=args.timeout,
            )
            hosted = invoke_hosted_agent(contract)
            assert_showcase_response("hosted agent", hosted, require_tool=True)
            _print_json(
                {
                    "preflight": checks,
                    "prompt_version": prompt_version,
                    "memory": "optional: prepare separately with the memory command",
                    "hosted_version": hosted_version,
                    "hosted_smoke": hosted,
                }
            )
        elif args.command in {"verify", "showcase"}:
            started_at = datetime.now(UTC)
            prompt = invoke_prompt_agent(contract)
            hosted = invoke_hosted_agent(contract)
            assert_showcase_response("prompt agent", prompt)
            assert_showcase_response("hosted agent", hosted, require_tool=True)
            result: dict[str, Any] = {
                "prompt_agent": prompt,
                "hosted_agent": hosted,
            }
            if args.trace:
                result["trace_records"] = verify_trace(
                    contract,
                    started_at=started_at,
                    trace_ids=hosted["trace_ids"],
                    timeout_seconds=args.timeout,
                )
            _print_json(result)
        elif args.command == "cleanup":
            _print_json(cleanup(contract))
        return 0
    except (DemoError, HttpResponseError, httpx.HTTPError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
