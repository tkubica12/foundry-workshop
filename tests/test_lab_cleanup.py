"""Cleanup must be idempotent and must only claim a failure when one exists.

An attendee reaches cleanup at the end of a timed lab, sometimes twice, and sometimes
after deleting an agent by hand in the portal. An agent that is already gone satisfies
the goal of the command, so it must not be reported as retained and must not fail the
run. A nonzero exit here sends a facilitator hunting for resources that do not exist.
"""

from __future__ import annotations

import argparse
import json
import sys
import hashlib
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from azure.core.exceptions import ResourceNotFoundError

SCRIPTS = Path(__file__).resolve().parents[1] / "teacher" / "demos" / "build-host-agent" / "harness"
sys.path.insert(0, str(SCRIPTS))

import lab  # noqa: E402

PREFIX = "ch2-seat-001-abc123-"
ENDPOINT = "https://example/api/projects/p"
METADATA = {
    "workshop_owner": lab.OWNER_METADATA, "workshop_run": "abc123",
    "workshop_seat": "seat-001",
    "workshop_project": hashlib.sha256(ENDPOINT.encode()).hexdigest(),
}


class FakeAgents:
    def __init__(self, existing: set[str], broken: dict[str, Exception] | None = None) -> None:
        self.existing = set(existing)
        self.broken = broken or {}
        self.attempted: list[str] = []

    def list_versions(self, name, **_kwargs):
        if name not in self.existing:
            raise ResourceNotFoundError("Agent not found")
        return [{"version": "1", "metadata": METADATA}]

    def get(self, name):
        if name not in self.existing:
            raise ResourceNotFoundError("Agent not found")
        return {"instance_identity": {"principal_id": f"identity-{name}"}}

    def delete_version(self, **_kwargs):
        pass

    def delete(self, name: str) -> None:
        self.attempted.append(name)
        if name in self.broken:
            raise self.broken[name]
        if name not in self.existing:
            raise ResourceNotFoundError("Agent not found")
        self.existing.remove(name)


class FakeProject:
    def __init__(self, agents: FakeAgents) -> None:
        self.agents = agents


@pytest.fixture
def cleanup_run(tmp_path, monkeypatch):
    """Run cmd_cleanup against a fake project and return its exit code and output."""

    def run(created: list[str], existing: set[str], broken: dict[str, Exception] | None = None):
        card = tmp_path / "card.json"
        card.write_text(
            json.dumps(
                {
                    "run_id": "abc123",
                    "seat_id": "seat-001",
                    "project_endpoint": ENDPOINT,
                    "resources": [
                        {"name": PREFIX + name, "versions": ["1"], "status": "retained"}
                        for name in created
                    ],
                    "sections": {"guardrail": {"agents_created": created}},
                }
            ),
            encoding="utf-8",
        )
        agents = FakeAgents(
            {PREFIX + name for name in existing},
            {PREFIX + name: error for name, error in (broken or {}).items()},
        )

        @contextmanager
        def fake_client(*_args, **_kwargs):
            yield FakeProject(agents)

        monkeypatch.setattr(lab, "project_client", fake_client)
        monkeypatch.setattr(lab, "resolve", lambda _args: SimpleNamespace(
            project_endpoint=ENDPOINT, seat_id="seat-001",
        ))
        args = argparse.Namespace(card=str(card), tenant=None)
        code = lab.cmd_cleanup(args)
        return code, agents

    return run


def test_deleting_agents_that_exist_reports_success(cleanup_run, capsys):
    code, agents = cleanup_run(["agent-a", "agent-b"], {"agent-a", "agent-b"})
    out = capsys.readouterr().out
    assert code == 0
    assert f"deleted {PREFIX}agent-a" in out
    assert f"deleted {PREFIX}agent-b" in out
    assert "NOT deleted" not in out
    assert agents.existing == set()


def test_an_agent_that_is_already_gone_is_not_a_failure(cleanup_run, capsys):
    code, _ = cleanup_run(["agent-a"], set())
    out = capsys.readouterr().out
    assert code == 0, "an absent agent already satisfies the goal of cleanup"
    assert f"already gone {PREFIX}agent-a" in out
    assert "NOT deleted" not in out


def test_running_cleanup_twice_is_safe(cleanup_run, capsys):
    first, _ = cleanup_run(["agent-a", "agent-b"], {"agent-a", "agent-b"})
    capsys.readouterr()
    second, _ = cleanup_run(["agent-a", "agent-b"], set())
    out = capsys.readouterr().out
    assert (first, second) == (0, 0)
    assert out.count("already gone") == 2
    assert "Your project is clean" in out


def test_a_real_failure_still_fails_loudly(cleanup_run, capsys):
    code, _ = cleanup_run(
        ["agent-a", "agent-b"],
        {"agent-a", "agent-b"},
        broken={"agent-b": PermissionError("denied")},
    )
    out = capsys.readouterr().out
    assert code == 1
    assert f"deleted {PREFIX}agent-a" in out
    assert f"NOT deleted {PREFIX}agent-b" in out
    assert "1 agent(s) still exist and need manual removal." in out


def test_every_recorded_agent_is_attempted_even_after_one_fails(cleanup_run):
    _, agents = cleanup_run(
        ["agent-a", "agent-b", "agent-c"],
        {"agent-a", "agent-b", "agent-c"},
        broken={"agent-a": PermissionError("denied")},
    )
    assert agents.attempted == [PREFIX + name for name in ("agent-a", "agent-b", "agent-c")]
    assert agents.existing == {PREFIX + "agent-a"}


def preflight_fixture(tmp_path, monkeypatch, *, outcome=None, interrupted=False):
    from types import SimpleNamespace
    from seat import SeatContract, SharedModel

    contract = SeatContract(
        "seat-001", "https://example/api/projects/p",
        (
            SharedModel("gateway/gpt-5.6-luna", "Microsoft / OpenAI"),
            SharedModel("gateway/Mistral-Large-3", "Mistral AI"),
        ),
        "local", "policy", "/policy",
    )
    card = tmp_path / "preflight.json"
    creations = []

    class Agents:
        def list_versions(self, name, **_kw):
            return [
                {"version": str(index + 1), "metadata": entry["metadata"]}
                for index, entry in enumerate(creations) if entry["agent_name"] == name
            ]

        def create_version(self, **kwargs):
            creations.append(kwargs)
            return SimpleNamespace(version=str(len(creations)))

        def get(self, name):
            if not any(entry["agent_name"] == name for entry in creations):
                raise ResourceNotFoundError("synthetic absent agent")
            return {"instance_identity": {"principal_id": "synthetic-principal"}}

        def delete(self, _name):
            return None

        def delete_version(self, **_kwargs):
            return None

    class OpenAI:
        def close(self):
            pass

    class Project:
        agents = Agents()

        def get_openai_client(self):
            if interrupted:
                raise KeyboardInterrupt("synthetic interruption after creation")
            return OpenAI()

    @contextmanager
    def client(*_a, **_kw):
        yield Project()

    monkeypatch.setattr(lab, "resolve", lambda _a: contract)
    monkeypatch.setattr(lab, "project_client", client)
    monkeypatch.setattr(
        lab, "call_agent",
        lambda *_a: outcome or lab.CallOutcome(True, 0.1, text="READY", status="completed"),
    )
    return argparse.Namespace(card=str(card), tenant=None, run_id="abc123"), card, creations


def test_preflight_failed_inference_never_confirms_access(tmp_path, monkeypatch, capsys):
    args, card, _ = preflight_fixture(
        tmp_path, monkeypatch,
        outcome=lab.CallOutcome(False, 1, error_kind="TimeoutError", detail="synthetic timeout"),
    )
    assert lab.cmd_preflight(args) == 1
    assert "Access confirmed" not in capsys.readouterr().out
    assert "TimeoutError" in card.read_text()


def test_preflight_journals_before_next_network_operation(tmp_path, monkeypatch):
    args, card, _ = preflight_fixture(tmp_path, monkeypatch, interrupted=True)
    with pytest.raises(KeyboardInterrupt):
        lab.cmd_preflight(args)
    persisted = json.loads(card.read_text())
    assert persisted["project_endpoint"] == "https://example/api/projects/p"
    assert persisted["resources"][0]["name"] == "ch2-seat-001-abc123-preflight"
    assert persisted["resources"][0]["versions"] == ["1"]


@pytest.mark.parametrize(
    "bad",
    ["all_answered", "local_error", "timeout", "missing_attribution", "both_blocked", "baseline_blocked"],
)
def test_inconclusive_guardrail_never_claims_verified_gap(bad, capsys):
    trials = [
        {"version_label": label, "prompt_label": prompt, "outcome": "answered", "blocklist": None}
        for label in ("baseline (no policy)", "governed")
        for prompt in ("sentinel", "control")
    ]
    trials[2].update(outcome="blocked by synthetic-list", blocklist="synthetic-list")
    if bad == "all_answered":
        trials[2].update(outcome="answered", blocklist=None)
    elif bad == "local_error":
        trials[2].update(outcome="failed (PermissionError)", blocklist=None)
    elif bad == "timeout":
        trials[3]["outcome"] = "failed (TimeoutError)"
    elif bad == "missing_attribution":
        trials[2].update(outcome="blocked", blocklist=None)
    elif bad == "both_blocked":
        trials[3]["outcome"] = "blocked by synthetic-list"
    else:
        trials[0]["outcome"] = "blocked by synthetic-list"
    lab._explain_guardrail(trials, {"outcome": "answered"})
    output = capsys.readouterr().out
    assert "verified" not in output.lower()
    assert "inconclusive" in output.lower()


def owned_card(tmp_path, *, endpoint=ENDPOINT, identity=None):
    path = tmp_path / "owned-card.json"
    resource = {"name": PREFIX + "agent", "versions": ["1"], "status": "retained"}
    if identity:
        resource["identity"] = identity
    path.write_text(json.dumps({
        "run_id": "abc123", "seat_id": "seat-001", "project_endpoint": endpoint,
        "resources": [resource], "sections": {},
    }))
    return path


def cleanup_args(path):
    return argparse.Namespace(card=str(path), tenant=None)


def fake_cleanup_client(monkeypatch, agents):
    @contextmanager
    def client(*_a, **_k):
        yield SimpleNamespace(agents=agents)
    monkeypatch.setattr(lab, "project_client", client)
    monkeypatch.setattr(lab, "resolve", lambda _a: SimpleNamespace(
        project_endpoint=ENDPOINT, seat_id="seat-001",
    ))


def test_cleanup_refuses_changed_project_without_touching_cloud(tmp_path, monkeypatch):
    path = owned_card(tmp_path, endpoint="https://example/api/projects/other")
    fake_cleanup_client(monkeypatch, object())
    with pytest.raises(ValueError, match="project"):
        lab.cmd_cleanup(cleanup_args(path))


@pytest.mark.parametrize("changed", ["owner", "run", "seat", "project", "identity"])
def test_cleanup_refuses_foreign_same_name_object(tmp_path, monkeypatch, changed):
    path = owned_card(tmp_path, identity="original")
    agents = FakeAgents({PREFIX + "agent"})
    metadata = dict(METADATA)
    if changed != "identity":
        key = {"owner": "workshop_owner", "run": "workshop_run", "seat": "workshop_seat", "project": "workshop_project"}[changed]
        metadata[key] = "foreign"
    agents.list_versions = lambda *_a, **_k: [{"version": "1", "metadata": metadata}]
    agents.get = lambda _name: {"instance_identity": {"principal_id": "replacement" if changed == "identity" else "original"}}
    fake_cleanup_client(monkeypatch, agents)
    assert lab.cmd_cleanup(cleanup_args(path)) == 1
    assert agents.attempted == []
    assert json.loads(path.read_text())["resources"][0]["status"] == "retained"


def test_cleanup_refuses_legacy_name_only_card(tmp_path, monkeypatch):
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({"run_id": "abc123", "seat_id": "seat-001",
                                "sections": {"guardrail": {"agents_created": [PREFIX + "agent"]}}}))
    fake_cleanup_client(monkeypatch, object())
    with pytest.raises(ValueError, match="project"):
        lab.cmd_cleanup(cleanup_args(path))


def test_cleanup_retry_reconciles_retained_empty_parent(tmp_path, monkeypatch):
    path = owned_card(tmp_path)
    class Agents(FakeAgents):
        versions = [{"version": "1", "metadata": METADATA}]
        failures = 1
        def list_versions(self, *_a, **_k):
            return self.versions
        def delete_version(self, **_kw):
            self.versions = []
        def delete(self, name):
            if self.failures:
                self.failures -= 1
                raise PermissionError("synthetic denied")
            super().delete(name)
    agents = Agents({PREFIX + "agent"})
    fake_cleanup_client(monkeypatch, agents)
    assert lab.cmd_cleanup(cleanup_args(path)) == 1
    retained = json.loads(path.read_text())["resources"][0]
    assert retained["validated_deletion_identity"] == f"identity-{PREFIX}agent"
    assert lab.cmd_cleanup(cleanup_args(path)) == 0
    assert agents.existing == set()
    assert json.loads(path.read_text())["resources"][0]["status"] == "removed"


def test_preflight_refuses_stale_run_card(tmp_path, monkeypatch):
    args, path, creations = preflight_fixture(tmp_path, monkeypatch)
    path.write_text(json.dumps({"run_id": "older", "seat_id": "seat-001",
                                "project_endpoint": ENDPOINT, "resources": [], "sections": {}}))
    with pytest.raises(ValueError, match="run_id"):
        lab.cmd_preflight(args)
    assert creations == []


@pytest.mark.parametrize("interrupt_after", [1, 2, 3])
def test_guardrail_journals_every_creation_before_interruption(tmp_path, monkeypatch, interrupt_after):
    args, path, _ = preflight_fixture(tmp_path, monkeypatch)
    assert lab.cmd_preflight(args) == 0
    args.skip_gateway = False
    original = lab.create_version
    count = 0
    def interrupt(*a, **kw):
        nonlocal count
        version = original(*a, **kw)
        count += 1
        if count == interrupt_after:
            raise KeyboardInterrupt("synthetic interrupted creation sequence")
        return version
    monkeypatch.setattr(lab, "create_version", interrupt)
    with pytest.raises(KeyboardInterrupt):
        lab.cmd_guardrail(args)
    resources = json.loads(path.read_text())["resources"]
    guardrail = next(row for row in resources if row["name"].endswith("-guardrail"))
    assert guardrail["versions"]
    if interrupt_after == 3:
        assert any("-gw-" in row["name"] and row["versions"] for row in resources)


def test_creation_intent_survives_lost_create_acknowledgement(tmp_path, monkeypatch):
    args, path, _ = preflight_fixture(tmp_path, monkeypatch)
    assert lab.cmd_preflight(args) == 0
    card = lab.open_card(args)
    class Agents:
        def list_versions(self, *_a, **_kw):
            raise ResourceNotFoundError("absent before creation")
        def create_version(self, **_kw):
            raise KeyboardInterrupt("server may have created the agent; acknowledgement lost")
        def get(self, _name):
            raise ResourceNotFoundError("absent before creation")
    with pytest.raises(KeyboardInterrupt):
        lab.create_version(SimpleNamespace(agents=Agents()), PREFIX + "pending", "local", "instructions", "test", card=card)
    resource = next(row for row in json.loads(path.read_text())["resources"] if row["name"].endswith("-pending"))
    assert resource["status"] == "creation_pending"
    assert resource["versions"] == []


def test_guardrail_command_fails_and_records_inconclusive_matrix(tmp_path, monkeypatch):
    args, path, _ = preflight_fixture(tmp_path, monkeypatch)
    assert lab.cmd_preflight(args) == 0
    args.skip_gateway = False
    assert lab.cmd_guardrail(args) == 1
    assert json.loads(path.read_text())["sections"]["guardrail"]["selective_control_proven"] is False


def test_preflight_preserves_successful_cleanup_journal(tmp_path, monkeypatch):
    args, path, _ = preflight_fixture(tmp_path, monkeypatch)
    assert lab.cmd_preflight(args) == 0
    data = json.loads(path.read_text())
    resource = data["resources"][0]
    assert resource["status"] == "removed"
    assert resource["validated_deletion_identity"] == "synthetic-principal"
    assert data["sections"]["cleanup"]["removed"] == [resource["name"]]
    assert data["sections"]["cleanup"]["failed_or_retained"] == []
    assert data["sections"]["preflight"]["warmup"]["text"] == "READY"


def test_preflight_keeps_failed_cleanup_evidence_actionable(tmp_path, monkeypatch, capsys):
    args, path, _ = preflight_fixture(tmp_path, monkeypatch)
    original_client = lab.project_client
    @contextmanager
    def client(*a, **kw):
        with original_client(*a, **kw) as project:
            def denied(_name):
                raise PermissionError("synthetic cleanup denial")
            project.agents.delete = denied
            yield project
    monkeypatch.setattr(lab, "project_client", client)
    assert lab.cmd_preflight(args) == 1
    data = json.loads(path.read_text())
    assert data["resources"][0]["status"] == "retained"
    assert "PermissionError" in data["sections"]["cleanup"]["failed_or_retained"][0]
    assert data["sections"]["preflight"]["warmup"]["text"] == "READY"
    assert "Access confirmed" not in capsys.readouterr().out
