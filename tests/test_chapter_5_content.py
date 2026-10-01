"""Corpus parity, judge/target separation and destructive-scope contracts."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/guides/chapter-5-knowledge-base.html"
DATASET = ROOT / "evals/grounding/instruments-evaluation.jsonl"


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_rows_and_downloads_match_manifest_pinned_sources():
    result = subprocess.run(
        [sys.executable, str(ROOT / "evals/grounding/prepare.py"), "--check", "--bundle"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rows = [json.loads(line) for line in DATASET.read_text().splitlines()]
    assert len(rows) == len({row["query"] for row in rows}) == len({row["case_id"] for row in rows}) == 100
    assert sorted({row["evidence_type"] for row in rows}) == [
        "annotated-image", "diagram", "image-only-chart", "prose", "table",
    ]
    for kind in {row["evidence_type"] for row in rows}:
        assert sum(row["evidence_type"] == kind for row in rows) == 20
    for row in rows:
        assert row["document"] in row["query"]
        assert isinstance(row["ground_truth"], str)
        assert "Curated reference" in row["context"]
        assert row["ground_truth"] in row["context"]
        assert "response" not in row
    with zipfile.ZipFile(ROOT / "docs/assets/knowledge-base/instruments-pdfs.zip") as archive:
        assert len(archive.namelist()) == 20
        assert all(name.endswith(".pdf") and "/" not in name for name in archive.namelist())
    core = [json.loads(line) for line in (DATASET.parent / "instruments-evaluation-core.jsonl").read_text().splitlines()]
    assert len(core) == len({row["document"] for row in core}) == 20
    assert core[0] == rows[0]
    assert all(row in rows for row in core)
    assert all(sum(row["evidence_type"] == kind for row in core) == 4 for kind in {row["evidence_type"] for row in rows})


def test_manual_query_is_an_actual_dataset_row():
    rows = [json.loads(line) for line in DATASET.read_text().splitlines()]
    source = GUIDE.read_text(encoding="utf-8")
    assert rows[0]["query"] in source
    assert "Alder Works, line S1; 1962" in source
    for phrase in ("judge-only", "not a verbatim extracted passage", "Response completeness",
                   "missing Indexer is expected", "image-only", "resume-cleanup",
                   "Project Managed Identity"):
        assert phrase in source
    assert "groundedness score alone" not in source.lower() or "not completion" in source


def test_core_uses_prepared_keyless_source_and_separates_upload_extension():
    source = GUIDE.read_text(encoding="utf-8")
    core = source.split('<article class="card" id="card-source">', 1)[1].split("</article>", 1)[0]
    steps, optional = core.split('Optional: upload your own PDF source', 1)
    assert "Add sources &rarr; Use existing sources" in steps
    assert "20 files" in steps
    assert "no Storage account" in steps
    assert "<strong>Upload files</strong>" not in steps
    assert "API key authentication is disabled" in optional
    assert "HTTP 429" in optional and "at most twice" in optional
    assert "Search Index Data Contributor" in source
    assert "Cognitive Services User" in source
    assert "Do not create a new service during the core lab" in source
    assert "Spain Central lists semantic ranking but not agentic retrieval" in source
    assert "one-document probe does not certify all charts" in source
    assert "facilitator's assigned private Blob container" not in source


def sample_state():
    group = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-knowledge-rehearsal-11111111"
    account = group + "/providers/Microsoft.CognitiveServices/accounts/fwknowledge22222222"
    return {
        "subscription": "00000000-0000-0000-0000-000000000001",
        "ownership": "00000000-0000-0000-0000-000000000002",
        "group": "rg-knowledge-rehearsal-11111111", "group_id": group,
        "account": "fwknowledge22222222", "account_id": account,
        "project_id": account + "/projects/instruments",
        "search_id": group + "/providers/Microsoft.Search/searchServices/fwknowledge-33333333",
        "search_endpoint": "https://fwknowledge-33333333.search.windows.net",
        "project_endpoint": "https://fwknowledge22222222.services.ai.azure.com/api/projects/instruments",
        "openai_endpoint": "https://fwknowledge22222222.openai.azure.com",
        "tier": "basic", "region": "swedencentral", "search_region": "westeurope",
    }


@pytest.mark.parametrize("key,value", [
    ("account_id", "/subscriptions/foreign/resourceGroups/production/providers/accounts/other"),
    ("search_endpoint", "https://unrelated.search.windows.net"),
    ("project_endpoint", "https://attacker.example"),
    ("group", "production"),
])
def test_tampered_scope_is_rejected(key, value):
    azure = load(ROOT / "student/labs/knowledge-base/scripts/azure.py")
    state = sample_state()
    azure.validate_state(state)
    state[key] = value
    with pytest.raises(RuntimeError):
        azure.validate_state(state)


def test_cleanup_refuses_unexpected_resources_or_ownership(monkeypatch, tmp_path):
    azure = load(ROOT / "student/labs/knowledge-base/scripts/azure.py")
    state = sample_state()
    calls = []

    def fake_arm(client, method, path, **kwargs):
        calls.append(method)
        if path.endswith("/resources"):
            return {"value": [{"id": state["group_id"] + "/providers/Microsoft.Compute/virtualMachines/unexpected"}]}
        return {"tags": {"rehearsal-id": state["ownership"], "purpose": azure.PURPOSE}}

    monkeypatch.setattr(azure, "arm", fake_arm)
    with pytest.raises(RuntimeError, match="Unexpected resource"):
        azure.cleanup(object(), state, tmp_path / "state.json", state["group"])
    assert "DELETE" not in calls
    with pytest.raises(RuntimeError, match="exact rehearsal group"):
        azure.cleanup(object(), state, tmp_path / "state.json", "different-group")


def test_native_evaluator_maps_references_only_to_judges(monkeypatch, tmp_path):
    azure = load(ROOT / "student/labs/knowledge-base/scripts/azure.py")
    state = sample_state()
    state["baseline_version"] = "1"
    requests = []
    monkeypatch.setattr(azure, "ownership", lambda *_: {})

    def fake_project(client, state, method, route, body=None):
        requests.append((method, route, body))
        if route.endswith("/output_items?limit=100"):
            data = json.loads(DATASET.read_text().splitlines()[0])
            data["sample.output_text"] = "I don't know."
            return {"data": [{"id": "row", "status": "completed", "datasource_item": data,
                             "results": [
                                 {"name": "corpus-groundedness", "metric": "groundedness",
                                  "status": "completed", "score": 1, "passed": False, "threshold": 3},
                                 {"name": "reference-completeness", "metric": "response_completeness",
                                  "status": "completed", "score": 1, "passed": False, "threshold": 3},
                             ]}], "has_more": False}
        if route.endswith("/runs") and method == "POST":
            return {"id": "run"}
        if route.endswith("/evals"):
            return {"id": "evaluation"}
        return {"status": "completed", "result_counts": {"errored": 0}}

    monkeypatch.setattr(azure, "project", fake_project)
    azure.evaluate(object(), state, tmp_path / "state.json", "baseline", 1)
    definition = next(body for _, route, body in requests if route.endswith("/evals"))
    run = next(body for method, route, body in requests if method == "POST" and route.endswith("/runs"))
    assert definition["testing_criteria"][0]["data_mapping"]["context"] == "{{item.context}}"
    assert definition["testing_criteria"][1]["evaluator_name"] == "builtin.response_completeness"
    messages = run["data_source"]["input_messages"]["template"]
    assert messages == [{"type": "message", "role": "user", "content": {"type": "input_text", "text": "{{item.query}}"}}]
    assert run["data_source"]["target"]["version"] == "1"


def manual_response():
    url = "https://fictional.search.windows.net/indexes/instrument-files-index/docs/acoustic-001"
    return {"status": "completed", "output": [
        {"type": "mcp_call", "name": "knowledge_base_retrieve", "server_label": "instrument-knowledge",
         "output": json.dumps({"documents": [{"url": url, "content": json.dumps({
             "metadata_storage_path": "acoustic-guitar.pdf", "snippet": "Alder Works, line S1; 1962."
         })}]})},
        {"type": "message", "content": [{"type": "output_text", "text": "Alder Works, line S1; 1962.",
                                        "annotations": [{"type": "url_citation", "url": url}]}]},
    ]}


@pytest.mark.parametrize("fault", ["wrong-tool", "wrong-document", "no-citation", "wrong-citation", "missing-line", "wrong-line-prefix", "wrong-year-prefix"])
def test_manual_probe_rejects_plausible_but_unverified_answers(fault):
    azure = load(ROOT / "student/labs/knowledge-base/scripts/azure.py")
    value = manual_response()
    azure.validate_manual_response(value)
    if fault == "wrong-tool":
        value["output"][0]["name"] = "unrelated_tool"
    elif fault == "wrong-document":
        value["output"][0]["output"] = value["output"][0]["output"].replace("acoustic-guitar.pdf", "electric-guitar.pdf")
    elif fault == "no-citation":
        value["output"][1]["content"][0]["annotations"] = []
    elif fault == "wrong-citation":
        value["output"][1]["content"][0]["annotations"][0]["url"] += "-wrong"
    elif fault == "missing-line":
        value["output"][1]["content"][0]["text"] = "Alder Works; 1962."
    elif fault == "wrong-line-prefix":
        value["output"][1]["content"][0]["text"] = "Alder Works, line S10; 1962."
    else:
        value["output"][1]["content"][0]["text"] = "Alder Works, line S1; 19620."
    with pytest.raises(RuntimeError):
        azure.validate_manual_response(value)


@pytest.mark.parametrize("fault", ["no-scores", "duplicate-case", "score-error", "not-numeric"])
def test_evaluation_probe_rejects_completed_but_unscored_rows(fault):
    azure = load(ROOT / "student/labs/knowledge-base/scripts/azure.py")
    rows = [{"case_id": "instrument-001"}]
    value = [{"id": "row", "status": "completed", "datasource_item": {"case_id": "instrument-001", "sample.output_text": "I don't know."}, "results": [
        {"name": "corpus-groundedness", "metric": "groundedness", "status": "completed", "score": 1, "passed": False, "threshold": 3},
        {"name": "reference-completeness", "metric": "response_completeness", "status": "completed", "score": 1, "passed": False, "threshold": 3},
    ]}]
    azure.validate_evaluation_results(value, rows)
    if fault == "no-scores":
        value[0]["results"] = []
    elif fault == "duplicate-case":
        value.append(value[0])
    elif fault == "score-error":
        value[0]["results"][0]["status"] = "failed"
    else:
        value[0]["results"][0]["score"] = "1"
    with pytest.raises(RuntimeError):
        azure.validate_evaluation_results(value, rows)


def test_cleanup_does_not_repeat_an_already_accepted_delete(monkeypatch, tmp_path):
    azure = load(ROOT / "student/labs/knowledge-base/scripts/azure.py")
    state = sample_state()
    groups = iter([{"properties": {"provisioningState": "Deleting"}}, None])
    monkeypatch.setattr(azure, "ownership", lambda *_: next(groups))
    monkeypatch.setattr(azure, "resource_ledger", lambda *_: [])
    monkeypatch.setattr(azure, "arm", lambda *_args, **_kwargs: pytest.fail("Already accepted deletion must not be resubmitted"))
    azure.cleanup(object(), state, tmp_path / "state.json", state["group"])
    assert state["cleaned"] is True


def test_paginated_resource_ledger_fails_closed(monkeypatch):
    azure = load(ROOT / "student/labs/knowledge-base/scripts/azure.py")
    monkeypatch.setattr(azure, "arm", lambda *_args, **_kwargs: {"value": [], "nextLink": "more"})
    with pytest.raises(RuntimeError, match="incomplete scope"):
        azure.resource_ledger(object(), sample_state())


@pytest.mark.parametrize("dark", [False, True])
def test_guide_mobile_offline_copy_and_download_links(dark, tmp_path):
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, offline=True,
                                      color_scheme="dark" if dark else "light")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(GUIDE.as_uri())
        page.locator('[data-action="expand-all"]').click()
        page.evaluate("""Object.defineProperty(navigator,'clipboard',{
            configurable:true,value:{writeText:async text=>{window.copied=text;}}
        })""")
        page.locator("#manual-query [data-lab-copy]").click()
        expected = json.loads(DATASET.read_text().splitlines()[0])["query"]
        page.wait_for_function("(text)=>window.copied===text", arg=expected)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        for href in ("../assets/knowledge-base/instruments-pdfs.zip",
                     "../assets/knowledge-base/instruments-evaluation-core.jsonl",
                     "../assets/knowledge-base/instruments-evaluation.jsonl"):
            assert page.locator(f'a[download][href="{href}"]').count() == 1
        assert not errors
        context.close()
        browser.close()
