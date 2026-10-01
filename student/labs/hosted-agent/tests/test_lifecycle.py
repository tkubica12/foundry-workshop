import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

spec = importlib.util.spec_from_file_location("lab07", Path(__file__).resolve().parents[1] / "scripts" / "lab07.py")
lab07 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab07)

SUBSCRIPTION = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(lab07, "PRIVATE", tmp_path)
    config = {
        "project_endpoint": "https://fictional.services.ai.azure.com/api/projects/workshop",
        "project_resource_id": f"/subscriptions/{SUBSCRIPTION}/resourceGroups/workshop/providers/Microsoft.CognitiveServices/accounts/fictional/projects/workshop",
        "agent_name": "lab07-test-s01", "owner": "lab07-test", "model": "prepared-model",
        "image": "ghcr.io/fictional/workshop@sha256:" + "0" * 64,
        "environment": {"TOOLBOX_ENDPOINT": "https://fictional.services.ai.azure.com/api/projects/workshop/toolboxes/tools/versions/1/mcp?api-version=v1"},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    state = tmp_path / "state.json"
    args = ["lab07.py", "deploy", "--config", str(config_path), "--state", str(state), "--confirm"]
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setattr(lab07.shutil, "which", lambda _: "az")
    monkeypatch.setattr(lab07.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, SUBSCRIPTION + "\n", ""))
    return config, config_path, state, args


class Project:
    def __init__(self, agents):
        self.agents = agents

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_uncertain_creation_is_not_retried(setup, monkeypatch):
    _, _, state, _ = setup
    creates = []

    def missing(*args):
        raise ResourceNotFoundError("not found")

    def uncertain(*args, **kwargs):
        creates.append(args)
        raise HttpResponseError("connection lost after create")

    monkeypatch.setattr(lab07, "AIProjectClient", lambda **kw: Project(SimpleNamespace(
        get=missing, create_version=uncertain,
    )))
    with pytest.raises(HttpResponseError):
        lab07.main()
    assert json.loads(state.read_text())["status"] == "create-requested"
    with pytest.raises(RuntimeError, match="uncertain"):
        lab07.main()
    assert len(creates) == 1
    assert not state.with_suffix(".lock").exists()


def test_cleanup_never_deletes_concurrently_added_version_or_parent(setup, monkeypatch):
    _, config_path, state, args = setup
    config = lab07.read_config(config_path)
    state.write_text(json.dumps({"config": lab07.fingerprint(config), "version": "1", "status": "active"}))
    args[1] = "cleanup"
    deleted = []
    owned = SimpleNamespace(metadata={"lab07_owner": config["owner"], "lab07_config": lab07.fingerprint(config)})

    def get_version(*a):
        # Another deployment can now add version 2; cleanup must stay on 1.
        return owned

    agents = SimpleNamespace(
        get_version=get_version,
        delete_version=lambda name, version, **kwargs: deleted.append((name, version)),
        delete=lambda *a, **k: pytest.fail("Parent deletion exceeds receipt scope"),
    )
    monkeypatch.setattr(lab07, "AIProjectClient", lambda **kw: Project(agents))
    lab07.main()
    lab07.main()
    assert deleted == [(config["agent_name"], "1")]
    assert json.loads(state.read_text())["status"] == "cleaned"


def test_wrong_live_owner_blocks_deletion(setup, monkeypatch):
    _, config_path, state, args = setup
    config = lab07.read_config(config_path)
    state.write_text(json.dumps({"config": lab07.fingerprint(config), "version": "1", "status": "active"}))
    args[1] = "cleanup"
    agents = SimpleNamespace(get_version=lambda *a: SimpleNamespace(metadata={"lab07_owner": "someone-else"}))
    monkeypatch.setattr(lab07, "AIProjectClient", lambda **kw: Project(agents))
    with pytest.raises(RuntimeError, match="ownership"):
        lab07.main()


def test_equals_argument_cannot_bypass_receipt_lock(setup):
    _, _, state, args = setup
    index = args.index("--state")
    args[index:index + 2] = ["--state=" + str(state)]
    state.with_suffix(".lock").touch()
    with pytest.raises(RuntimeError, match="lock"):
        lab07.main()


def test_literal_secret_configuration_is_rejected(setup):
    config, path, _, _ = setup
    config["environment"] = {
        "PARTNERS_MCP_URL": "https://partners.example.com/mcp",
        "COMPLAINTS_MCP_URL": "https://complaints.example.com/mcp",
        "MCP_API_KEY": "not-a-real-key",
    }
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="placeholder"):
        lab07.read_config(path)
