import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import invoke


class Client:
    def __init__(self, create):
        self.responses = SimpleNamespace(with_raw_response=SimpleNamespace(create=create))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture
def setup(tmp_path, monkeypatch):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"config": "scope", "version": "1", "status": "active"}))
    conversation = tmp_path / "read.json"
    args = ["invoke.py", "start", "--config", str(tmp_path / "config.json"),
            "--state", str(state), "--conversation", str(conversation)]
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setattr(invoke, "read_config", lambda _: {
        "project_endpoint": "https://fictional.services.ai.azure.com/api/projects/workshop",
        "agent_name": "lab07-test-s01",
    })
    monkeypatch.setattr(invoke, "fingerprint", lambda _: "scope")
    monkeypatch.setattr(invoke, "private_path", lambda p: p.resolve())
    monkeypatch.setattr(invoke, "checked_version", lambda *a: SimpleNamespace(status="active"))
    return args, conversation


def test_start_saves_response_trace_and_requires_individual_approval(setup, monkeypatch):
    args, conversation = setup
    sent = []
    result = {"id": "resp-1", "status": "completed", "output": [
        {"type": "mcp_approval_request", "id": "approval-1", "name": "get_partner", "arguments": "{}"},
    ]}

    def create(**kwargs):
        sent.append(kwargs)
        return SimpleNamespace(
            headers={"x-ms-request-id": "request-1"},
            parse=lambda: SimpleNamespace(model_dump=lambda **_: result),
        )

    client = Client(create)
    project = Client(create)
    project.agents = SimpleNamespace(list_versions=lambda _: [SimpleNamespace(version="1")])
    project.get_openai_client = lambda **kwargs: client
    monkeypatch.setattr(invoke, "AIProjectClient", lambda **kwargs: project)
    invoke.main()
    saved = json.loads(conversation.read_text())
    assert saved["response"] == result
    assert saved["trace_id"] in sent[0]["extra_headers"]["traceparent"]
    assert not conversation.with_suffix(".pending.json").exists()
    args[1] = "approve"
    with pytest.raises(ValueError, match="approval ID"):
        invoke.main()
    assert len(sent) == 1
    args += ["--approval-id", "approval-1"]
    invoke.main()
    assert sent[1]["input"] == [{"type": "mcp_approval_response", "approval_request_id": "approval-1", "approve": True}]


def test_uncertain_turn_cannot_be_replayed(setup, monkeypatch):
    _, conversation = setup

    def uncertain(**kwargs):
        raise RuntimeError("uncertain transport")

    client = Client(uncertain)
    project = Client(uncertain)
    project.agents = SimpleNamespace(list_versions=lambda _: [SimpleNamespace(version="1")])
    project.get_openai_client = lambda **kwargs: client
    monkeypatch.setattr(invoke, "AIProjectClient", lambda **kwargs: project)
    with pytest.raises(RuntimeError, match="uncertain transport"):
        invoke.main()
    assert conversation.with_suffix(".pending.json").exists()
    with pytest.raises(RuntimeError, match="Previous turn"):
        invoke.main()


@pytest.mark.parametrize("operation", ["start", "approve", "reject"])
def test_concurrent_and_stale_turns_cannot_replay(setup, monkeypatch, operation):
    args, conversation = setup
    args[1] = operation
    if operation != "start":
        conversation.write_text(json.dumps({"config": "scope", "response": {
            "id": "old-response", "output": [{"type": "mcp_approval_request", "id": "approval-1"}],
        }}))
        args += ["--approval-id", "approval-1"]
    entered = threading.Event()
    finish = threading.Event()
    sent = []
    errors = []
    result = {"id": "new-response", "status": "completed", "output": []}

    def create(**kwargs):
        sent.append(kwargs)
        entered.set()
        assert finish.wait(10)
        return SimpleNamespace(headers={}, parse=lambda: SimpleNamespace(model_dump=lambda **_: result))

    client = Client(create)
    project = Client(create)
    project.agents = SimpleNamespace(list_versions=lambda _: [SimpleNamespace(version="1")])
    project.get_openai_client = lambda **kwargs: client
    monkeypatch.setattr(invoke, "AIProjectClient", lambda **kwargs: project)

    def first():
        try:
            invoke.main()
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=first)
    thread.start()
    try:
        assert entered.wait(10)
        with pytest.raises(RuntimeError, match="conversation lock"):
            invoke.main()
    finally:
        finish.set()
        thread.join(10)
    assert not thread.is_alive() and not errors
    with pytest.raises((RuntimeError, ValueError)):
        invoke.main()
    assert len(sent) == 1
    assert not conversation.with_suffix(".lock").exists()
