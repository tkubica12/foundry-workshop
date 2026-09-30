from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tomllib
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from azure.ai.projects.models import MemoryStoreDefaultOptions
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from openai import RateLimitError
from httpx import Request, Response

ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = ROOT / "teacher" / "demos" / "build-host-agent"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


demo = load_module("chapter2_demo", DEMO_ROOT / "scripts" / "demo.py")
agent = load_module("chapter2_agent", DEMO_ROOT / "agent" / "main.py")


def agent_details(principal_id="agent-principal"):
    return {
        "instance_identity": {
            "principal_id": principal_id,
        }
    }


def test_parse_contract_uses_published_teacher_outputs():
    project_id = (
        "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/"
        "accounts/teacher/projects/demo"
    )
    contract = demo.parse_contract(
        {
            "tenant_id": "tenant",
            "platform_outputs": {
                "teacher_application_insights_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Insights/components/appi",
                "teacher_foundry_id": project_id.rsplit("/projects/", 1)[0],
                "teacher_log_analytics_workspace_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.OperationalInsights/workspaces/law",
                "teacher_memory_chat_model": "memory-chat",
                "teacher_memory_embedding_model": "memory-embedding",
                "teacher_model_reference": "shared-ai-gateway/model",
                "teacher_project_endpoint": "https://example/api/projects/demo",
                "teacher_project_id": project_id,
            },
        }
    )

    assert contract.subscription_id == "sub"
    assert contract.tenant_id == "tenant"
    assert contract.model_reference == "shared-ai-gateway/model"
    assert contract.memory_chat_model == "memory-chat"
    assert contract.memory_embedding_model == "memory-embedding"


def test_parse_contract_rejects_incomplete_platform():
    with pytest.raises(demo.DemoError, match="missing"):
        demo.parse_contract({"tenant_id": "tenant", "platform_outputs": {}})


def test_memory_models_require_platform_contract():
    contract = demo.PlatformContract(
        subscription_id="sub",
        tenant_id="tenant",
        project_endpoint="https://example",
        project_id="/subscriptions/sub/projects/example",
        foundry_id="foundry",
        model_reference="connected/chat",
        memory_chat_model=None,
        memory_embedding_model=None,
        application_insights_id="appi",
        log_analytics_workspace_id="law",
    )

    with pytest.raises(demo.DemoError, match="Memory models are absent"):
        demo._memory_models(contract)


def test_reuse_checks_only_latest_agent_version():
    class Version(dict):
        @property
        def version(self):
            return self["version"]

    newer_mismatch = Version(
        version="2",
        status="active",
        metadata={
            "workshop_owner": demo.OWNER_METADATA,
            "content_sha256": "invalid-experiment",
        },
    )
    class Agents:
        def list_versions(self, _name, *, include_drafts, order, limit):
            assert include_drafts is False
            assert order == "desc"
            assert limit == 1
            return [newer_mismatch]

    project = SimpleNamespace(agents=Agents())

    assert demo._find_reusable_version(project, "agent", "current") is None

    newer_mismatch["metadata"]["content_sha256"] = "current"

    assert demo._find_reusable_version(project, "agent", "current") is newer_mismatch


def test_reuse_accepts_latest_nonnumeric_released_version():
    class Version(dict):
        @property
        def version(self):
            return self["version"]

    released = Version(
        version="release-blue",
        draft=False,
        status="active",
        metadata={
            "workshop_owner": demo.OWNER_METADATA,
            "content_sha256": "current",
        },
    )
    class Agents:
        def list_versions(self, _name, *, include_drafts, order, limit):
            assert include_drafts is False
            assert order == "desc"
            assert limit == 1
            return [released]

    project = SimpleNamespace(agents=Agents())

    assert demo._find_reusable_version(project, "agent", "current") is released


def test_memory_showcase_uses_distinct_scopes_and_synthetic_fact():
    assert demo.MEMORY_SCOPE != demo.MEMORY_ISOLATED_SCOPE
    assert "GREEN-742" in demo.MEMORY_FACT
    assert "STOCK-318" in demo.MEMORY_DISCUSSION_START
    assert "STOCK-318" in demo.MEMORY_DISCUSSION_CLOSE
    assert "GREEN-742" not in demo.MEMORY_RECALL_QUESTION
    assert "STOCK-318" not in demo.MEMORY_RECALL_QUESTION
    assert "STOCK-318" not in demo.MEMORY_SUMMARY_SEARCH_QUERY
    assert "synthetic" in demo.MEMORY_FACT.lower()
    assert "clinical" in demo.MEMORY_INSTRUCTIONS.lower()


def test_memory_response_retries_rate_limit(monkeypatch):
    class Responses:
        attempts = 0

        def create(self, **_kwargs):
            self.attempts += 1
            if self.attempts == 1:
                response = Response(
                    429,
                    headers={"retry-after-ms": "20000"},
                    request=Request("POST", "https://example/responses"),
                )
                raise RateLimitError(
                    "rate limited",
                    response=response,
                    body={"additionalInfo": {"request_id": "request-123"}},
                )
            return "recalled"

    responses = Responses()
    client = type("Client", (), {"responses": responses})()
    delays: list[float] = []
    monkeypatch.setattr(demo.time, "sleep", delays.append)

    result = demo._create_response_with_retry(client, input="recall")

    assert result == "recalled"
    assert responses.attempts == 2
    assert delays == [20]


def test_memory_response_bounds_output_tokens():
    class Responses:
        def create(self, **kwargs):
            return kwargs

    client = type("Client", (), {"responses": Responses()})()

    result = demo._create_memory_response(client, input="recall")

    assert result["max_output_tokens"] == 200


def test_memory_fallback_requires_prevalidated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "STATE_PATH", tmp_path / "missing.json")

    with pytest.raises(demo.DemoError, match="no prevalidated Memory result"):
        demo.memory_fallback()


def test_memory_fallback_is_explicitly_labeled(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "memory_showcase": {
                    "memory_items": 1,
                    "profile_recalled_in_new_conversation": "GREEN-742",
                    "chat_summary_recalled_contextually": "STOCK-318",
                },
                "memory_validated_at": "2026-07-29T07:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(demo, "STATE_PATH", state_path)

    result = demo.memory_fallback()

    assert result["prevalidated"] is True
    assert result["validated_at"] == "2026-07-29T07:00:00+00:00"


def test_memory_ttl_serializes_to_one_day():
    options = demo._memory_store_options()

    assert options.as_dict()["default_ttl_seconds"] == 86400
    assert options.user_profile_enabled is True
    assert options.chat_summary_enabled is True
    assert options.procedural_memory_enabled is False


def test_memory_store_reuse_requires_exact_options():
    expected = demo._memory_store_options()
    drifted = MemoryStoreDefaultOptions(
        user_profile_enabled=True,
        user_profile_details=expected.user_profile_details,
        chat_summary_enabled=True,
        procedural_memory_enabled=True,
        default_ttl_seconds=expected.default_ttl_seconds,
    )

    assert demo._memory_store_options_match(expected) is True
    assert demo._memory_store_options_match(drifted) is False
    assert demo._memory_store_options_match(object()) is False


def test_memory_kind_handles_sdk_enum_and_string():
    enum_item = type("Item", (), {"kind": demo.MemoryItemKind.CHAT_SUMMARY})()
    string_item = type("Item", (), {"kind": "user_profile"})()

    assert demo._memory_kind(enum_item) == "chat_summary"
    assert demo._memory_kind(string_item) == "user_profile"


def _run_mocked_memory_showcase(monkeypatch, *, leak_source=None):
    events = []
    response_calls = []

    class Conversations:
        next_id = 0

        def create(self):
            self.next_id += 1
            conversation = SimpleNamespace(id=f"conversation-{self.next_id}")
            events.append(("conversation.create", conversation.id))
            return conversation

        def delete(self, conversation_id):
            events.append(("conversation.delete", conversation_id))

    class Responses:
        def create(self, **kwargs):
            response_calls.append(kwargs)
            scope = kwargs["extra_headers"]["x-memory-user-id"]
            if scope == demo.MEMORY_ISOLATED_SCOPE:
                output = "GREEN-742 leaked" if leak_source == "agent" else "unknown"
            elif kwargs["input"] == demo.MEMORY_RECALL_QUESTION:
                output = "GREEN-742"
            else:
                output = "acknowledged"
            return SimpleNamespace(output_text=output)

    class OpenAI:
        conversations = Conversations()
        responses = Responses()

        def close(self):
            events.append(("openai.close", None))

    class Project:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get_openai_client(self):
            return OpenAI()

    memories = [
        SimpleNamespace(kind="user_profile", content="GREEN-742"),
        SimpleNamespace(kind="chat_summary", content="STOCK-318 no transfer"),
    ]
    summary = SimpleNamespace(kind="chat_summary", content="STOCK-318 no transfer")

    monkeypatch.setattr(
        demo,
        "ensure_memory_agent",
        lambda _contract, **_kwargs: "1",
    )
    monkeypatch.setattr(demo, "project_client", lambda _contract: Project())
    monkeypatch.setattr(
        demo,
        "_clear_memory_scope",
        lambda _project, scope: events.append(("scope.clear", scope)),
    )

    def wait_for_kinds(_project, *, scope, timeout_seconds, required_kinds):
        events.append(("memory.wait", scope, timeout_seconds, required_kinds))
        return memories

    def wait_for_summary(_project, *, scope, query, timeout_seconds):
        events.append(("summary.wait", scope, query, timeout_seconds))
        return [summary], summary.content

    monkeypatch.setattr(demo, "_wait_for_memory_kinds", wait_for_kinds)
    monkeypatch.setattr(demo, "_wait_for_contextual_summary", wait_for_summary)
    monkeypatch.setattr(
        demo,
        "_search_contextual_memories",
        lambda _project, *, scope, query: (
            [summary] if leak_source == "contextual" else []
        ),
    )
    monkeypatch.setattr(
        demo,
        "_search_static_memories",
        lambda _project, *, scope: (
            [SimpleNamespace(kind="user_profile", content="transformed leak")]
            if leak_source == "static"
            else []
        ),
    )
    monkeypatch.setattr(demo, "_save_state", lambda values: events.append(("save", values)))

    result = demo.invoke_memory_showcase(object(), timeout_seconds=120)
    return result, events, response_calls


def test_memory_showcase_orders_scopes_and_separates_conversations(monkeypatch):
    result, events, calls = _run_mocked_memory_showcase(monkeypatch)

    assert events[:2] == [
        ("scope.clear", demo.MEMORY_SCOPE),
        ("scope.clear", demo.MEMORY_ISOLATED_SCOPE),
    ]
    assert [call["conversation"] for call in calls] == [
        "conversation-1",
        "conversation-1",
        "conversation-1",
        "conversation-2",
        "conversation-3",
    ]
    assert events.index(("conversation.delete", "conversation-1")) < next(
        index for index, event in enumerate(events) if event[0] == "summary.wait"
    )
    assert demo.MEMORY_SUMMARY_SEARCH_QUERY not in [
        call["input"] for call in calls
    ]
    assert result["memory_kinds"] == ["chat_summary", "user_profile"]
    assert result["isolated_static_memory_items"] == 0
    assert result["isolated_chat_summary_items"] == 0


@pytest.mark.parametrize("leak_source", ["static", "contextual", "agent"])
def test_memory_showcase_rejects_isolated_scope_leaks(monkeypatch, leak_source):
    with pytest.raises(demo.DemoError, match="crossed user scopes"):
        _run_mocked_memory_showcase(monkeypatch, leak_source=leak_source)


def test_clear_memory_scope_waits_until_stale_items_are_gone(monkeypatch):
    class Stores:
        responses = [[SimpleNamespace(content="stale")], []]

        def delete_scope(self, *, name, scope):
            assert name == demo.MEMORY_STORE_NAME
            assert scope == demo.MEMORY_SCOPE

        def list_memories(self, *, name, scope):
            assert name == demo.MEMORY_STORE_NAME
            assert scope == demo.MEMORY_SCOPE
            return self.responses.pop(0)

    project = SimpleNamespace(
        beta=SimpleNamespace(memory_stores=Stores()),
    )
    sleeps = []
    monkeypatch.setattr(demo.time, "sleep", sleeps.append)

    demo._clear_memory_scope(project, demo.MEMORY_SCOPE)

    assert sleeps == [2]


def test_memory_reset_refuses_unowned_agent_versions(monkeypatch):
    class Version(dict):
        @property
        def version(self):
            return self["version"]

    class Agents:
        def list_versions(self, name, include_drafts):
            assert name == demo.MEMORY_AGENT_NAME
            assert include_drafts is True
            return [Version(version="9", metadata={"workshop_owner": "someone-else"})]

        def delete_version(self, **_kwargs):
            raise AssertionError("unowned version must not be deleted")

    class Project:
        agents = Agents()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(demo, "project_client", lambda _contract: Project())

    with pytest.raises(demo.DemoError, match="unowned versions"):
        demo.reset_memory_resources(object())


def test_memory_reset_recovers_after_agent_deleted_store_retained(
    tmp_path, monkeypatch
):
    shared = {
        "agent_exists": True,
        "store_exists": True,
        "store_delete_attempts": 0,
    }

    class Version(dict):
        @property
        def version(self):
            return self["version"]

    class Agents:
        def list_versions(self, name, include_drafts):
            assert name == demo.MEMORY_AGENT_NAME
            assert include_drafts is True
            if not shared["agent_exists"]:
                raise demo.ResourceNotFoundError(message="agent missing")
            return [
                Version(
                    version="1",
                    metadata={"workshop_owner": demo.OWNER_METADATA},
                )
            ]

        def delete_version(self, **_kwargs):
            return None

        def get(self, name):
            assert name == demo.MEMORY_AGENT_NAME
            if not shared["agent_exists"]:
                raise demo.ResourceNotFoundError(message="agent missing")
            return agent_details()

        def delete(self, name):
            assert name == demo.MEMORY_AGENT_NAME
            if not shared["agent_exists"]:
                raise demo.ResourceNotFoundError(message="missing")
            shared["agent_exists"] = False

    class Stores:
        def get(self, *, name):
            assert name == demo.MEMORY_STORE_NAME
            if not shared["store_exists"]:
                raise demo.ResourceNotFoundError(message="store missing")
            return SimpleNamespace(
                metadata={"workshop_owner": demo.OWNER_METADATA}
            )

        def delete(self, *, name):
            assert name == demo.MEMORY_STORE_NAME
            shared["store_delete_attempts"] += 1
            if shared["store_delete_attempts"] == 1:
                raise HttpResponseError(message="transient")
            shared["store_exists"] = False

    class Project:
        agents = Agents()
        beta = SimpleNamespace(memory_stores=Stores())

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "memory_showcase": {"memory_items": 2},
                "memory_validated_at": "2026-07-29T07:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(demo, "STATE_PATH", state_path)
    monkeypatch.setattr(demo, "project_client", lambda _contract: Project())

    with pytest.raises(demo.DemoError, match="memory reset incomplete"):
        demo.reset_memory_resources(object())

    assert shared["agent_exists"] is False
    assert shared["store_exists"] is True
    assert state_path.exists()

    result = demo.reset_memory_resources(object())

    assert result["agent_versions"] == []
    assert result["memory_store"] == demo.MEMORY_STORE_NAME
    assert shared["store_exists"] is False
    assert not state_path.exists()


@pytest.mark.parametrize("resource", ["version", "agent", "store"])
def test_memory_reset_accepts_only_typed_absence(tmp_path, monkeypatch, resource):
    class Version(dict):
        @property
        def version(self):
            return self["version"]

    class Agents:
        def list_versions(self, _name, include_drafts):
            assert include_drafts is True
            return [
                Version(
                    version="1",
                    metadata={"workshop_owner": demo.OWNER_METADATA},
                )
            ]

        def delete_version(self, **_kwargs):
            if resource == "version":
                raise demo.ResourceNotFoundError(message="already absent")

        def get(self, _name):
            return agent_details()

        def delete(self, _name):
            if resource == "agent":
                raise demo.ResourceNotFoundError(message="already absent")

    class Stores:
        def get(self, *, name):
            assert name == demo.MEMORY_STORE_NAME
            return SimpleNamespace(
                metadata={"workshop_owner": demo.OWNER_METADATA}
            )

        def delete(self, *, name):
            assert name == demo.MEMORY_STORE_NAME
            if resource == "store":
                raise demo.ResourceNotFoundError(message="already absent")

    class Project:
        agents = Agents()
        beta = SimpleNamespace(memory_stores=Stores())

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(demo, "project_client", lambda _contract: Project())
    monkeypatch.setattr(demo, "STATE_PATH", tmp_path / "missing-state.json")

    demo.reset_memory_resources(object())


def test_memory_reset_rejects_generic_http_404(tmp_path, monkeypatch):
    class Version(dict):
        @property
        def version(self):
            return self["version"]

    class Agents:
        def list_versions(self, _name, include_drafts):
            assert include_drafts is True
            return [
                Version(
                    version="1",
                    metadata={"workshop_owner": demo.OWNER_METADATA},
                )
            ]

        def delete_version(self, **_kwargs):
            return None

        def get(self, _name):
            return agent_details()

        def delete(self, _name):
            raise HttpResponseError(message="generic 404", status_code=404)

    class Stores:
        def get(self, *, name):
            assert name == demo.MEMORY_STORE_NAME
            raise demo.ResourceNotFoundError(message="store absent")

    class Project:
        agents = Agents()
        beta = SimpleNamespace(memory_stores=Stores())

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(demo, "project_client", lambda _contract: Project())
    monkeypatch.setattr(demo, "STATE_PATH", tmp_path / "state.json")

    with pytest.raises(demo.DemoError, match="generic 404"):
        demo.reset_memory_resources(object())


def test_memory_reset_refuses_existing_empty_agent(monkeypatch):
    class Agents:
        delete_called = False

        def list_versions(self, _name, include_drafts):
            assert include_drafts is True
            return []

        def get(self, _name):
            return agent_details()

        def delete(self, _name):
            self.delete_called = True

    agents = Agents()
    project = SimpleNamespace(agents=agents)

    class Project:
        def __enter__(self):
            return project

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(demo, "project_client", lambda _contract: Project())

    with pytest.raises(demo.DemoError, match="no versions"):
        demo.reset_memory_resources(object())

    assert agents.delete_called is False


def test_memory_reset_recovers_retained_empty_agent(tmp_path, monkeypatch):
    shared = {
        "versions_exist": True,
        "parent_delete_attempts": 0,
        "store_exists": True,
    }

    class Version(dict):
        @property
        def version(self):
            return self["version"]

    class Agents:
        def list_versions(self, _name, include_drafts):
            assert include_drafts is True
            if shared["versions_exist"]:
                return [
                    Version(
                        version="1",
                        metadata={"workshop_owner": demo.OWNER_METADATA},
                    )
                ]
            return []

        def get(self, _name):
            return agent_details("retained-agent-principal")

        def delete_version(self, **_kwargs):
            shared["versions_exist"] = False

        def delete(self, _name):
            shared["parent_delete_attempts"] += 1
            if shared["parent_delete_attempts"] == 1:
                raise HttpResponseError(message="transient parent failure")

    class Stores:
        def get(self, *, name):
            assert name == demo.MEMORY_STORE_NAME
            if not shared["store_exists"]:
                raise demo.ResourceNotFoundError(message="store absent")
            return SimpleNamespace(
                metadata={"workshop_owner": demo.OWNER_METADATA}
            )

        def delete(self, *, name):
            assert name == demo.MEMORY_STORE_NAME
            shared["store_exists"] = False

    class Project:
        agents = Agents()
        beta = SimpleNamespace(memory_stores=Stores())

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    state_path = tmp_path / "state.json"
    monkeypatch.setattr(demo, "STATE_PATH", state_path)
    monkeypatch.setattr(demo, "project_client", lambda _contract: Project())

    with pytest.raises(demo.DemoError, match="transient parent failure"):
        demo.reset_memory_resources(object())

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["validated_agent_deletions"][demo.MEMORY_AGENT_NAME] == (
        "retained-agent-principal"
    )
    assert shared["versions_exist"] is False
    assert shared["store_exists"] is True

    result = demo.reset_memory_resources(object())

    assert result["agent_versions"] == []
    assert result["memory_store"] == demo.MEMORY_STORE_NAME
    assert shared["store_exists"] is False
    assert not state_path.exists()


def test_partial_cleanup_reports_scope_and_retains_state(tmp_path, monkeypatch):
    class Version(dict):
        @property
        def version(self):
            return self["version"]

    versions = [
        Version(version="1", metadata={"workshop_owner": demo.OWNER_METADATA})
    ]

    class Agents:
        def list_versions(self, _name, include_drafts):
            assert include_drafts is True
            return versions

        def delete_version(self, *, agent_name, agent_version, force):
            assert force is True
            if agent_name == demo.MEMORY_AGENT_NAME:
                raise HttpResponseError(message=f"retained {agent_version}")

        def get(self, name):
            return agent_details(f"principal-{name}")

        def delete(self, _name):
            return None

    class MemoryStores:
        def get(self, *, name):
            assert name == demo.MEMORY_STORE_NAME
            return type(
                "Store",
                (),
                {"metadata": {"workshop_owner": demo.OWNER_METADATA}},
            )()

        def delete(self, *, name):
            assert name == demo.MEMORY_STORE_NAME

    class Project:
        agents = Agents()
        beta = type("Beta", (), {"memory_stores": MemoryStores()})()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    state_path = tmp_path / "state.json"
    state_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(demo, "STATE_PATH", state_path)
    monkeypatch.setattr(demo, "project_client", lambda _contract: Project())

    with pytest.raises(demo.DemoError, match="failed_or_retained") as failure:
        demo.cleanup(object())

    assert demo.MEMORY_AGENT_NAME in str(failure.value)
    assert state_path.exists()


def test_source_archive_is_deterministic_and_minimal():
    first = demo.create_source_archive()
    second = demo.create_source_archive()

    assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()
    with zipfile.ZipFile(BytesIO(first)) as archive:
        assert archive.namelist() == ["main.py", "requirements.txt"]
        assert ".env" not in archive.namelist()


def test_hosted_requirements_match_locked_versions():
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = {
        package["name"].lower().replace("_", "-"): package["version"]
        for package in lock["package"]
    }
    requirements = (
        DEMO_ROOT / "agent" / "requirements.txt"
    ).read_text(encoding="utf-8").splitlines()

    for line in requirements:
        requirement = line.strip()
        if not requirement or requirement.startswith("#"):
            continue
        name, version = requirement.split("==", 1)
        normalized_name = name.split("[", 1)[0].lower().replace("_", "-")
        assert locked[normalized_name] == version


def test_shortfall_tool_is_deterministic():
    result = agent.calculate_shortfall.func(
        current_stock=8,
        reserved_stock=3,
        forecast_demand=14,
    )

    assert json.loads(result) == {
        "available_stock": 5,
        "forecast_demand": 14,
        "shortfall": 9,
    }


def test_shortfall_rejects_negative_values():
    with pytest.raises(ValueError, match="non-negative"):
        agent.calculate_shortfall.func(
            current_stock=-1,
            reserved_stock=0,
            forecast_demand=1,
        )


def test_scenario_and_system_prompt_are_synthetic_and_non_clinical():
    assert "Synthetic store" in demo.STOCK_EXCEPTION
    assert "Never provide medical advice" in agent.SYSTEM_PROMPT
    assert "claim access to live systems" in agent.SYSTEM_PROMPT


def test_response_text_reads_responses_api_shape():
    payload = {
        "output": [
            {
                "content": [
                    {"type": "output_text", "text": "PRIORITY: high"},
                    {"type": "output_text", "text": "\nNEXT ACTION: escalate"},
                ]
            }
        ]
    }

    assert demo._response_text(payload) == "PRIORITY: high\nNEXT ACTION: escalate"


GOOD_TRIAGE = (
    "PRIORITY\nHigh. Available stock is 5 units.\n"
    "NEXT ACTION\nThe shortfall is 9 units. Raise a replenishment request.\n"
    "ESCALATE WHEN\nThe delivery slips."
)
GOOD_FOLLOW_UP = "The shortfall is 9 units. First raise a replenishment request."


@pytest.mark.parametrize(
    ("first", "follow_up"),
    [
        (GOOD_TRIAGE.replace("5 units", "8 units"), GOOD_FOLLOW_UP),
        (GOOD_TRIAGE.replace("9 units", "6 units"), GOOD_FOLLOW_UP),
        (GOOD_TRIAGE, "The shortfall is 6 units. First raise a replenishment request."),
        (GOOD_TRIAGE, "I cannot remember the previous turn."),
        (GOOD_TRIAGE + "\nOffer a substitute product.", GOOD_FOLLOW_UP),
        (GOOD_TRIAGE, GOOD_FOLLOW_UP + " I checked the live inventory."),
    ],
)
def test_showcase_rejects_wrong_or_unsafe_outcomes(first, follow_up):
    with pytest.raises(demo.DemoError):
        demo.assert_showcase_response("prompt agent", {"first": first, "follow_up": follow_up})


def test_memory_fallback_command_never_resolves_live_contract(monkeypatch, capsys):
    def no_contract(_args):
        raise demo.DemoError("offline labctl unavailable")

    monkeypatch.setattr(demo, "_contract_for", no_contract)
    monkeypatch.setattr(
        demo, "memory_fallback",
        lambda: {"prevalidated": True, "validated_at": "2026-07-29T07:00:00+00:00"},
    )
    assert demo.main(["memory-fallback"]) == 0
    assert "prevalidated" in capsys.readouterr().out


def test_prepare_does_not_require_optional_memory(monkeypatch):
    monkeypatch.setattr(demo, "_contract_for", lambda _args: object())
    monkeypatch.setattr(demo, "preflight", lambda _contract: {})
    monkeypatch.setattr(demo, "ensure_prompt_agent", lambda _contract: "1")
    monkeypatch.setattr(demo, "deploy_hosted_agent", lambda _contract, **_kw: "1")
    monkeypatch.setattr(demo, "invoke_hosted_agent", lambda _contract: {})
    monkeypatch.setattr(demo, "assert_showcase_response", lambda *_a, **_kw: None)

    def unavailable(*_a, **_kw):
        raise demo.DemoError("Memory is unavailable")

    monkeypatch.setattr(demo, "invoke_memory_showcase", unavailable)
    assert demo.main(["prepare"]) == 0


def platform_contract(**changes):
    values = dict(
        subscription_id="sub", tenant_id="tenant",
        project_endpoint="https://example/api/projects/demo",
        project_id="/subscriptions/sub/projects/demo", foundry_id="foundry",
        model_reference="connected/chat", memory_chat_model=None,
        memory_embedding_model=None, application_insights_id="appi",
        log_analytics_workspace_id="/subscriptions/sub/workspaces/law",
    )
    return demo.PlatformContract(**dict(values, **changes))


@pytest.mark.parametrize(
    "change",
    [
        {"model_reference": "connected/other"},
        {"project_endpoint": "https://example/api/projects/other"},
    ],
)
def test_hosted_reuse_fingerprint_includes_configuration(monkeypatch, change):
    from contextlib import nullcontext

    fingerprints = []
    monkeypatch.setattr(demo, "project_client", lambda _c: nullcontext(object()))
    monkeypatch.setattr(demo, "_assert_agent_deployment_owned", lambda *_args: None)

    def reuse(_project, _name, fingerprint, **_kwargs):
        fingerprints.append(fingerprint)
        return SimpleNamespace(version="1")

    monkeypatch.setattr(demo, "_find_reusable_version", reuse)
    monkeypatch.setattr(demo, "_route_hosted_version", lambda *_args: None)
    monkeypatch.setattr(demo, "_save_state", lambda _values: None)
    demo.deploy_hosted_agent(platform_contract())
    demo.deploy_hosted_agent(platform_contract(**change))
    assert fingerprints[0] != fingerprints[1]


@pytest.mark.parametrize("kind", ["prompt", "memory", "hosted"])
@pytest.mark.parametrize("new_version", [False, True])
@pytest.mark.parametrize("collision", ["foreign", "draft", "missing-owner", "empty", "empty-not-found-list"])
def test_teacher_deployment_rejects_collisions_before_any_mutation(
    monkeypatch, kind, new_version, collision,
):
    from contextlib import nullcontext

    def unexpected(*_args, **_kwargs):
        pytest.fail("A colliding agent must not cause creation or endpoint routing")

    class Agents:
        def list_versions(self, _name, *, include_drafts):
            assert include_drafts is True
            if collision == "empty-not-found-list":
                raise ResourceNotFoundError()
            if collision == "empty":
                return []
            owned = {"metadata": {"workshop_owner": demo.OWNER_METADATA}}
            foreign = {"metadata": {} if collision == "missing-owner" else {"workshop_owner": "foreign"}}
            if collision == "draft":
                foreign["draft"] = True
                return iter([owned, foreign])
            return iter([foreign, owned])

        def get(self, _name):
            return {}

        create_version = unexpected
        create_version_from_code = unexpected
        update_details = unexpected

    monkeypatch.setattr(demo, "project_client", lambda _contract: nullcontext(SimpleNamespace(agents=Agents())))
    monkeypatch.setattr(demo, "ensure_memory_store", unexpected)
    monkeypatch.setattr(demo, "_save_state", unexpected)
    contract = platform_contract(memory_chat_model="memory-chat", memory_embedding_model="memory-embedding")
    operation = {
        "prompt": demo.ensure_prompt_agent,
        "memory": demo.ensure_memory_agent,
        "hosted": demo.deploy_hosted_agent,
    }[kind]
    with pytest.raises(demo.DemoError, match="refusing to deploy or route"):
        operation(contract, new_version=new_version)


@pytest.mark.parametrize("existing", [False, True])
def test_teacher_deployment_allows_absent_or_fully_owned_agents(existing):
    class Agents:
        def list_versions(self, _name, *, include_drafts):
            assert include_drafts is True
            return [{"metadata": {"workshop_owner": demo.OWNER_METADATA}}] if existing else []

        def get(self, _name):
            if not existing:
                raise ResourceNotFoundError()
            return {}

    demo._assert_agent_deployment_owned(SimpleNamespace(agents=Agents()), demo.PROMPT_AGENT_NAME)


def test_hosted_routing_rechecks_ownership_before_updating_endpoint():
    class Agents:
        def list_versions(self, _name, *, include_drafts):
            assert include_drafts is True
            return [{"metadata": {"workshop_owner": "foreign"}}]

        def update_details(self, **_kwargs):
            pytest.fail("Foreign ownership must prevent endpoint updates")

    with pytest.raises(demo.DemoError, match="refusing to deploy or route"):
        demo._route_hosted_version(SimpleNamespace(agents=Agents()), "1")


@pytest.mark.parametrize("kind", ["prompt", "memory", "hosted"])
@pytest.mark.parametrize("new_version", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_owned_or_absent_teacher_agents_can_create_versions(monkeypatch, kind, new_version, existing):
    from contextlib import nullcontext

    class Version(dict):
        @property
        def version(self):
            return self["version"]

    calls = []
    versions = [
        Version(version="1", status="active", metadata={
            "workshop_owner": demo.OWNER_METADATA, "content_sha256": "old-content",
        }),
    ] if existing else []

    class Agents:
        def list_versions(self, _name, *, include_drafts, **_kwargs):
            return list(versions)

        def get(self, _name):
            if not versions:
                raise ResourceNotFoundError()
            return {}

        def create_version(self, **kwargs):
            calls.append("create")
            created = Version(version="2", status="active", metadata=kwargs["metadata"])
            versions.append(created)
            return created

        create_version_from_code = create_version

        def update_details(self, **_kwargs):
            calls.append("route")

    monkeypatch.setattr(demo, "project_client", lambda _contract: nullcontext(SimpleNamespace(agents=Agents())))
    monkeypatch.setattr(demo, "ensure_memory_store", lambda _contract: calls.append("memory-store"))
    monkeypatch.setattr(demo, "_wait_for_active", lambda *_args: versions[-1])
    monkeypatch.setattr(demo, "_save_state", lambda _values: None)
    contract = platform_contract(memory_chat_model="memory-chat", memory_embedding_model="memory-embedding")
    operation = {"prompt": demo.ensure_prompt_agent, "memory": demo.ensure_memory_agent, "hosted": demo.deploy_hosted_agent}[kind]
    assert operation(contract, new_version=new_version) == "2"
    assert calls == {"prompt": ["create"], "memory": ["memory-store", "create"], "hosted": ["create", "route"]}[kind]


def tool_output():
    return [
        {
            "type": "function_call", "name": "calculate_shortfall", "call_id": "call-1",
            "arguments": json.dumps({"current_stock": 8, "reserved_stock": 3, "forecast_demand": 14}),
        },
        {
            "type": "function_call_output", "call_id": "call-1",
            "output": json.dumps({"available_stock": 5, "forecast_demand": 14, "shortfall": 9}),
        },
    ]


def test_showcase_accepts_exact_tool_and_numerical_evidence():
    demo.assert_showcase_response(
        "hosted agent",
        {"first": GOOD_TRIAGE, "follow_up": GOOD_FOLLOW_UP, "first_output": tool_output()},
        require_tool=True,
    )


@pytest.mark.parametrize("bad", ["missing", "text_claim", "wrong_call_id", "wrong_arguments", "wrong_result"])
def test_showcase_rejects_missing_or_unrelated_tool_evidence(bad):
    output = tool_output()
    if bad == "missing":
        output = []
    elif bad == "text_claim":
        output = [{"type": "message", "content": [{"text": "I called calculate_shortfall and got 5/9"}]}]
    elif bad == "wrong_call_id":
        output[1]["call_id"] = "different-call"
    elif bad == "wrong_arguments":
        output[0]["arguments"] = '{"current_stock": 8, "reserved_stock": 0, "forecast_demand": 14}'
    else:
        output[1]["output"] = '{"available_stock": 8, "forecast_demand": 14, "shortfall": 6}'
    with pytest.raises(demo.DemoError, match="tool"):
        demo.assert_showcase_response(
            "hosted agent",
            {"first": GOOD_TRIAGE, "follow_up": GOOD_FOLLOW_UP, "first_output": output},
            require_tool=True,
        )


@pytest.mark.parametrize("field,value", [("cpu", "1"), ("memory", "2Gi"), ("runtime", "python_3_12"), ("protocol", "9.0.0")])
def test_hosted_fingerprint_covers_runtime_and_protocol(field, value):
    original = demo.hosted_definition(platform_contract())
    changed = demo.hosted_definition(platform_contract())
    if field == "runtime":
        changed.code_configuration.runtime = value
    elif field == "protocol":
        changed.protocol_versions[0].version = value
    else:
        setattr(changed, field, value)
    assert demo.hosted_fingerprint(b"source", original) != demo.hosted_fingerprint(b"source", changed)


def test_hosted_reuse_waits_on_matching_pending_attempt(monkeypatch):
    pending = {"status": "provisioning", "metadata": {
        "workshop_owner": demo.OWNER_METADATA, "content_sha256": "current",
    }}
    class Version(dict):
        version = "2"
    project = SimpleNamespace(agents=SimpleNamespace(list_versions=lambda *_a, **_k: [Version(pending)]))
    waited = []
    monkeypatch.setattr(demo, "_wait_for_active", lambda *a: waited.append(a) or "active")
    assert demo._find_reusable_version(
        project, "agent", "current", resume_pending=True, timeout_seconds=25,
    ) == "active"
    assert waited == [(project, "agent", "2", 25)]


def test_failed_latest_does_not_poison_next_attempt():
    failed = {"status": "failed", "metadata": {
        "workshop_owner": demo.OWNER_METADATA, "content_sha256": "current",
    }}
    project = SimpleNamespace(agents=SimpleNamespace(list_versions=lambda *_a, **_k: [failed]))
    assert demo._find_reusable_version(project, "agent", "current", resume_pending=True) is None


def test_preflight_without_contract_does_not_invoke_legacy_setup(monkeypatch, capsys):
    def forbidden(*_a, **_kw):
        raise AssertionError("legacy platform resolver must require explicit authorization")
    monkeypatch.setattr(demo, "load_contract", forbidden)
    assert demo.main(["preflight"]) == 1
    assert "--contract-file" in capsys.readouterr().err


def test_explicit_teacher_contract_is_parsed_without_platform_resolution(tmp_path, monkeypatch):
    path = tmp_path / "teacher.json"
    path.write_text(json.dumps(teacher_contract_payload()))
    monkeypatch.setattr(demo, "load_contract", lambda *_a: pytest.fail("unexpected platform resolver"))
    args = demo.build_parser().parse_args(["preflight", "--contract-file", str(path)])
    assert demo._contract_for(args).project_endpoint == "https://example/api/projects/p"


@pytest.mark.parametrize("returned_id,passes", [("1" * 32, True), ("2" * 32, False)])
def test_trace_verification_requires_exact_new_operation(monkeypatch, returned_id, passes):
    from datetime import UTC, datetime

    queries = []
    ticks = iter([0, 0, 2])
    monkeypatch.setattr(demo.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(demo.time, "sleep", lambda _s: None)
    monkeypatch.setattr(demo, "credential_for", lambda _c: SimpleNamespace(
        get_token=lambda _scope: SimpleNamespace(token="synthetic-token"),
    ))
    class Reply:
        def __init__(self, body):
            self.body = body
        def raise_for_status(self):
            pass
        def json(self):
            return self.body
    monkeypatch.setattr(demo.httpx, "get", lambda *_a, **_kw: Reply({"properties": {"customerId": "workspace"}}))
    def query(*_a, **kwargs):
        queries.append(kwargs["json"]["query"])
        return Reply({"tables": [{"rows": [[returned_id, 1]]}]})
    monkeypatch.setattr(demo.httpx, "post", query)
    kwargs = dict(started_at=datetime.now(UTC), trace_ids=["1" * 32], timeout_seconds=1)
    if passes:
        result = demo.verify_trace(platform_contract(), **kwargs)
        assert result == {"operation_ids": ["1" * 32], "records": 1}
    else:
        with pytest.raises(demo.DemoError, match="exact teacher traces"):
            demo.verify_trace(platform_contract(), **kwargs)
    assert 'OperationId in ("' + "1" * 32 + '")' in queries[0]


def test_trace_verification_refuses_missing_correlation_before_credentials(monkeypatch):
    from datetime import UTC, datetime
    monkeypatch.setattr(demo, "credential_for", lambda _c: pytest.fail("unexpected credential use"))
    with pytest.raises(demo.DemoError, match="exact invocation"):
        demo.verify_trace(platform_contract(), started_at=datetime.now(UTC), trace_ids=[])


def test_conversation_records_exact_requests_and_tool_evidence():
    calls, deleted = [], []
    class Response:
        status = "completed"
        def __init__(self, number):
            self.id = f"response-{number}"
            self.output_text = GOOD_TRIAGE if number == 1 else GOOD_FOLLOW_UP
        def model_dump(self):
            return {"output": tool_output() if self.id == "response-1" else []}
    class Responses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return Response(len(calls))
    client = SimpleNamespace(
        conversations=SimpleNamespace(
            create=lambda: SimpleNamespace(id="fresh-conversation"),
            delete=deleted.append,
        ),
        responses=Responses(), close=lambda: None,
    )
    project = SimpleNamespace(get_openai_client=lambda **_kw: client)
    result = demo._conversation(project, agent_name=demo.HOSTED_AGENT_NAME, agent_version=None)
    assert result["response_ids"] == ["response-1", "response-2"]
    assert len(set(result["trace_ids"])) == 2
    for index, call in enumerate(calls):
        assert call["conversation"] == "fresh-conversation"
        assert call["extra_headers"]["traceparent"].split("-")[1] == result["trace_ids"][index]
    assert calls[1]["input"] == demo.FOLLOW_UP
    assert deleted == ["fresh-conversation"]
    demo.assert_showcase_response("hosted", result, require_tool=True)


@pytest.mark.parametrize("bad", ["source", "project", "version", "route", "owner"])
def test_hosted_provenance_refuses_stale_source_or_wrong_route(monkeypatch, bad):
    contract = platform_contract()
    fingerprint = demo.hosted_fingerprint(demo.create_source_archive(), demo.hosted_definition(contract))
    state = {
        "project_endpoint": contract.project_endpoint,
        "deployment_sha256": fingerprint, "hosted_version": "2",
    }
    version = {"status": "active", "metadata": {
        "workshop_owner": demo.OWNER_METADATA, "content_sha256": fingerprint,
    }}
    rules = [{"agent_version": "2", "traffic_percentage": 100}]
    if bad == "source":
        state["deployment_sha256"] = "stale"
    elif bad == "project":
        state["project_endpoint"] = "https://example/api/projects/foreign"
    elif bad == "version":
        version["status"] = "failed"
    elif bad == "route":
        rules[0]["agent_version"] = "1"
    else:
        version["metadata"]["workshop_owner"] = "foreign"
    monkeypatch.setattr(demo, "_load_state", lambda: state)
    project = SimpleNamespace(agents=SimpleNamespace(
        get_version=lambda *_a: version,
        get=lambda *_a: {"agent_endpoint": {"version_selector": {"version_selection_rules": rules}}},
    ))
    with pytest.raises(demo.DemoError):
        demo._check_hosted_route(project, contract)


def test_local_showcase_checks_two_turns_tool_and_process_cleanup(monkeypatch):
    requests = []
    class Process:
        returncode = None
        stopped = False
        def poll(self):
            return None
        def terminate(self):
            self.stopped = True
        def wait(self, timeout):
            assert timeout == 15
    process = Process()
    monkeypatch.setattr(demo.subprocess, "Popen", lambda *_a, **_kw: process)
    monkeypatch.setattr(demo, "_available_port", lambda: 8088)
    class Client:
        def __enter__(self):
            return self
        def __exit__(self, *_a):
            pass
        def get(self, _url):
            return SimpleNamespace(is_success=True)
        def post(self, _url, *, json):
            requests.append(json)
            first = len(requests) == 1
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    "id": "local-1" if first else "local-2", "status": "completed",
                    "output_text": GOOD_TRIAGE if first else GOOD_FOLLOW_UP,
                    "output": tool_output() if first else [],
                },
            )
    monkeypatch.setattr(demo.httpx, "Client", lambda **_kw: Client())
    result = demo.invoke_local_agent(platform_contract())
    assert requests[1]["previous_response_id"] == "local-1"
    assert requests[1]["input"] == demo.FOLLOW_UP
    assert result["response_ids"] == ["local-1", "local-2"]
    assert process.stopped


@pytest.mark.parametrize("turn", ["first", "follow_up"])
@pytest.mark.parametrize("quantity", ["9.5", "9,000", "9e3", "9/2"])
def test_showcase_rejects_entire_wrong_numerical_claim_despite_correct_tool(turn, quantity):
    evidence = {
        "first": GOOD_TRIAGE, "follow_up": GOOD_FOLLOW_UP, "first_output": tool_output(),
    }
    evidence[turn] = evidence[turn].replace("9 units", f"{quantity} units")
    with pytest.raises(demo.DemoError):
        demo.assert_showcase_response("hosted", evidence, require_tool=True)


def teacher_contract_payload():
    scope = "/subscriptions/sub/resourceGroups/rg/providers/"
    foundry = scope + "Microsoft.CognitiveServices/accounts/teacher"
    return {
        "tenant_id": "tenant",
        "platform_outputs": {
            "teacher_project_id": foundry + "/projects/p",
            "teacher_foundry_id": foundry,
            "teacher_application_insights_id": scope + "Microsoft.Insights/components/appi",
            "teacher_log_analytics_workspace_id": scope + "Microsoft.OperationalInsights/workspaces/law",
            "teacher_project_endpoint": "https://example/api/projects/p",
            "teacher_model_reference": "connected/chat",
        },
    }


@pytest.mark.parametrize("field", sorted(demo.REQUIRED_PLATFORM_OUTPUTS) + ["tenant_id"])
@pytest.mark.parametrize("value", [None, "", "   ", True, {"unexpected": "value"}, 42])
def test_teacher_contract_rejects_unusable_required_values_before_external_work(
    tmp_path, monkeypatch, capsys, field, value,
):
    payload = teacher_contract_payload()
    target = payload if field == "tenant_id" else payload["platform_outputs"]
    target[field] = value
    path = tmp_path / "invalid-teacher.json"
    path.write_text(json.dumps(payload))
    monkeypatch.setenv("AZURE_TENANT_ID", "ambient-must-not-mask-invalid-input")
    monkeypatch.setattr(demo, "load_contract", lambda *_a: pytest.fail("external resolver"))
    monkeypatch.setattr(demo, "credential_for", lambda *_a: pytest.fail("credentials"))
    assert demo.main(["contract", "--contract-file", str(path)]) == 1
    error = capsys.readouterr().err
    assert field in error
    assert "unexpected" not in error


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example/api/projects/p", "https://example", "https://example/api/projects/",
        "https://user:password@example/api/projects/p", "https://example/api/projects/p?secret=x",
        "https://example/api/projects/p#fragment", "https://example/api/projects/other",
        "https://example:invalid/api/projects/p", "https://example\\bad/api/projects/p",
    ],
)
def test_teacher_contract_rejects_unusable_project_endpoint(endpoint):
    payload = teacher_contract_payload()
    payload["platform_outputs"]["teacher_project_endpoint"] = endpoint
    with pytest.raises(demo.DemoError, match="teacher_project_endpoint"):
        demo.parse_contract(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("teacher_project_id", "/subscriptions/sub/projects/p"),
        ("teacher_foundry_id", "foundry"),
        ("teacher_application_insights_id", "/subscriptions/sub/components/appi"),
        ("teacher_log_analytics_workspace_id", "/subscriptions/foreign/resourceGroups/rg/providers/Microsoft.OperationalInsights/workspaces/law"),
        ("teacher_foundry_id", "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foreign"),
    ],
)
def test_teacher_contract_rejects_invalid_or_conflicting_resource_scope(field, value):
    payload = teacher_contract_payload()
    payload["platform_outputs"][field] = value
    with pytest.raises(demo.DemoError, match=field):
        demo.parse_contract(payload)


def test_usable_teacher_contract_validates_without_ambient_tenant():
    parsed = demo.parse_contract(teacher_contract_payload())
    assert parsed.project_endpoint == "https://example/api/projects/p"
    assert parsed.subscription_id == "sub"
    assert parsed.tenant_id == "tenant"
