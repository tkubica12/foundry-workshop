"""Keep the Lab 1 deployment scope and recovery boundaries explicit."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guides" / "chapter-1-foundry-setup.html"


def test_primary_fallback_keeps_the_same_type_and_capacity():
    source = GUIDE.read_text(encoding="utf-8")
    primary = source.split('id="card-primary-model"', 1)[1].split("</article>", 1)[0]
    assert primary.index("gpt-6.1-sol") < primary.index("gpt-6-sol") < primary.index("gpt-5.6-sol")
    for required in (
        "exactly one primary", "Do not deploy all three", "Global Standard",
        "100000", "100,000 TPM", "Custom settings", "Default settings",
        "TPM is a rate limit, not a spending cap", "do not create a duplicate",
        "default guardrail", "do not increase capacity",
    ):
        assert required in primary


def test_additional_deployments_have_exact_allocations():
    source = GUIDE.read_text(encoding="utf-8")
    rows = re.findall(r"<tr><td><code>(.*?)</code>.*?</tr>", source)
    assert rows == ["gpt-6-luna", "FW-GLM-5.3-Flash"]
    table = source.split("<caption>Additional model deployments</caption>", 1)[1].split("</table>", 1)[0]
    assert table.count("<td>Global Standard</td>") == 2
    assert table.count("<td>50,000</td>") == 2
    assert "no substitute is specified for these two models" in source


def test_access_project_playground_and_recovery_are_concrete():
    source = GUIDE.read_text(encoding="utf-8")
    for required in (
        "https://ai.azure.com", "https://portal.azure.com",
        "existing resource group", "Sweden Central", "swedencentral",
        "workshop-&lt;seat-number&gt;", "Fireworks.EnableDeploy",
        "assigned Microsoft Entra account", "Advanced options",
        "Build &rarr; Models", "Discover &rarr; Models", "Succeeded",
        "each of your three", "up to 30 minutes", "not a completed checkpoint",
        "Do not register subscription-wide features",
        "30 seconds", "60 seconds", "The facilitator owns deletion",
        "Lab 1's three deployments do not replace those prerequisites",
        'id="resume-cleanup"', 'id="hello-prompt"', "outside Sweden",
    ):
        assert required.lower() in source.lower()


def test_agenda_allocates_lab_1_before_lab_2_without_extending_the_day():
    agenda = (ROOT / "AGENDA.md").read_text(encoding="utf-8")
    assert "09:20-09:45" in agenda
    assert "09:45-10:30" in agenda
    assert agenda.index("chapter-1-foundry-setup.html") < agenda.index("chapter-2-build-agent.html")
    assert "09:00-17:00" in agenda


def test_pending_fireworks_has_a_deferred_success_and_hello_check():
    source = GUIDE.read_text(encoding="utf-8")
    for required in (
        "finish pending GLM checks later", "do not wait past the core timebox",
        "defer its success check", "Not yet tested",
        "continue to the next lab after facilitator confirmation",
        "Final check, after pending work",
    ):
        assert required in source
