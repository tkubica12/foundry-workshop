"""Lab 04 inputs, operator safety contracts and the real local reading UI."""
import json
import re
import runpy
import sys
import types
from html import unescape
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/guides/chapter-4-connect-tools.html"
LAB = ROOT / "student/labs/connect-tools"


def snippet(identifier):
    match = re.search(rf'id="{identifier}".*?<pre><code>(.*?)</code>',
                      GUIDE.read_text(encoding="utf-8"), re.DOTALL)
    assert match, identifier
    return unescape(match.group(1))


def test_exact_prompts_and_instructions_match_source():
    assert snippet("tool-instructions") + "\n" == (LAB / "instructions.txt").read_text()
    prompts = json.loads((LAB / "prompts.json").read_text())
    for key in ("read", "create", "propose", "assign", "note"):
        assert snippet(key + "-prompt") == prompts[key]


def test_core_has_scoped_write_and_exact_trace_checkpoints():
    source = GUIDE.read_text(encoding="utf-8")
    for required in (
        "55 minutes", "Inspect observability / 15 minutes", "expected_version",
        "order_reference", "Application Insights", "gen_ai.response.id", "Conversation ID",
        "Trajectories", "Metadata", "readback", "approval", "shared, volatile",
        "Instructions are not access control", "does not enforce the approval pause",
        "do not complete this trace checkpoint", "never reset a shared server",
        "Specialties",
    ):
        if required == "Specialties":
            assert "<code>specialties</code>" in source
        else:
            assert required in source
    assert "delete_complaint" not in snippet("tool-instructions")
    assert "Do not assign a partner or add a note yet" in snippet("create-prompt")
    assert "Do not write anything yet" in snippet("propose-prompt")
    assert "Do not change its status or add a note" in snippet("assign-prompt")
    assert source.index('id="ch-traces"') < source.index('id="ch-extensions"')
    for required in ("Create toolbox", "Never auto-approve tools", "Approve once",
                     "Always approve all tools", "Type: Agent Identity", "27 characters",
                     "Input + Output", "gen_ai.tool.call.result"):
        assert required in source


@pytest.fixture
def operator_modules(monkeypatch):
    monkeypatch.setattr(sys, "path", sys.path.copy())
    dotenv = types.ModuleType("dotenv")
    dotenv.dotenv_values = lambda path: {}
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    verifier = types.ModuleType("verify")
    verifier.call = lambda *args: None
    verifier.mcp_client = lambda *args: None
    verifier.require = lambda condition, message: None
    monkeypatch.setitem(sys.modules, "verify", verifier)
    return (
        runpy.run_path(str(LAB / "scripts/prepare_toolbox.py")),
        runpy.run_path(str(LAB / "scripts/verify_journey.py")),
    )


def test_exact_tool_allowlist_excludes_destructive_and_unrelated_tools(operator_modules):
    prepare, verify = operator_modules
    assert set(prepare["ALLOWLIST"]["partners"]) == verify["PARTNERS"]
    assert set(prepare["ALLOWLIST"]["complaints"]) == verify["COMPLAINTS"]
    assert sum(map(len, prepare["ALLOWLIST"].values())) == 7
    assert snippet("partner-allowlist").split(",") == prepare["ALLOWLIST"]["partners"]
    assert snippet("complaint-allowlist").split(",") == prepare["ALLOWLIST"]["complaints"]
    assert not {"delete_complaint", "delete_partner", "put_partner", "transition_complaint", "update_complaint"} & set().union(*prepare["ALLOWLIST"].values())


def test_project_scope_must_match_exact_endpoint(operator_modules):
    prepare, _ = operator_modules
    resource = "/subscriptions/demo/resourceGroups/demo/providers/Microsoft.CognitiveServices/accounts/workshop/projects/seat"
    endpoint = "https://workshop.services.ai.azure.com/api/projects/seat"
    assert prepare["project_paths"](endpoint, resource) == (endpoint, "https://management.azure.com" + resource)
    for wrong in (
        endpoint.replace("https:", "http:"), endpoint.replace("workshop.", "different."),
        endpoint + "?token=invalid", endpoint.replace("/seat", "/other"),
        endpoint.replace("https://", "https://user@"),
    ):
        with pytest.raises(ValueError):
            prepare["project_paths"](wrong, resource)


def test_connections_refuse_unowned_or_changed_configuration(operator_modules):
    prepare, _ = operator_modules

    class Client:
        def __init__(self, properties):
            self.properties = properties
            self.writes = []

        def request(self, url, method="GET", data=None, **kwargs):
            if method != "GET":
                self.writes.append(data)
            return {"properties": self.properties}

    expected = {"category": "RemoteTool", "target": "https://example.com/mcp",
                "authType": "CustomKeys", "isSharedToAll": False}
    for current in (dict(expected, metadata={}),
                    dict(expected, target="https://different.example/mcp", metadata={"lab04_owner": "ours"}),
                    dict(expected, isSharedToAll=True, metadata={"lab04_owner": "ours"})):
        client = Client(current)
        with pytest.raises(RuntimeError):
            prepare["ensure_connection"](client, "https://management.azure.com/example", "lab04-s07-partners", expected, "ours")
        assert not client.writes
    client = Client(dict(expected, metadata={"lab04_owner": "ours"}))
    prepare["ensure_connection"](client, "https://management.azure.com/example", "lab04-s07-partners", expected, "ours")
    assert not client.writes


def test_partner_eligibility_checks_all_four_dimensions(operator_modules):
    _, verifier = operator_modules
    case = {"transaction_type": "repair", "instrument_family": "plucked_strings", "customer": {"country_code": "CZ"}}
    partner = {"status": "active", "address": {"country_code": "CZ"},
               "specialties": ["plucked_strings"], "services": ["repairs"]}
    assert verifier["eligible"](partner, case)
    for change in ({"status": "suspended"}, {"address": {"country_code": "DE"}},
                   {"specialties": ["brass"]}, {"services": ["sales"]}):
        assert not verifier["eligible"](dict(partner, **change), case)
    assert verifier["eligible"](partner, dict(case, transaction_type="warranty"))
    assert not verifier["eligible"](partner, dict(case, transaction_type="rental"))


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width,height", [(390, 844), (1280, 720)])
def test_reading_controls_copy_deep_links_and_no_overflow(theme, width, height):
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context(viewport={"width": width, "height": height},
                                      color_scheme=theme, reduced_motion="reduce", offline=True)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(GUIDE.as_uri() + "#card-traces")
            expect(page.locator("#card-traces")).to_have_attribute("data-open", "")
            page.locator('[data-action="expand-all"]').click()
            page.evaluate("""Object.defineProperty(navigator, "clipboard", {
                configurable: true, value: {writeText: async text => {window.copied = text;}}
            })""")
            for identifier in ("partner-allowlist", "complaint-allowlist",
                               "tool-instructions", "read-prompt", "create-prompt",
                               "propose-prompt", "assign-prompt", "note-prompt"):
                page.locator("#" + identifier + " [data-lab-copy]").click()
                page.wait_for_function("(text) => window.copied === text", arg=snippet(identifier))
            for _ in range(4):
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.locator('[data-action="toggle-accent"]').click()
            page.locator('[data-action="toggle-theme"]').focus()
            page.keyboard.press("Enter")
            expect(page.locator("html")).to_have_attribute("data-theme", "dark" if theme == "light" else "light")
            page.reload()
            expect(page.locator("html")).to_have_attribute("data-theme", "dark" if theme == "light" else "light")
            assert not errors
        finally:
            context.close()
            browser.close()
