"""Keep the customer baseline and PII evidence sequence aligned."""

from pathlib import Path
from html import unescape
import re


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guides" / "chapter-2-build-agent.html"


def source():
    return GUIDE.read_text(encoding="utf-8")


def snippet(identifier):
    match = re.search(
        rf'<div class="code" id="{identifier}">.*?<code>(.*?)</code>',
        source(), re.DOTALL,
    )
    assert match, f"Missing copyable snippet: {identifier}"
    return unescape(match.group(1))


def test_baseline_defines_task_not_personality_or_output_schema():
    instructions = snippet("baseline-instructions")
    assert "fictional click-and-collect" in instructions
    assert "facts supplied" in instructions
    assert "cannot look up orders" in instructions
    assert "medical advice" not in instructions
    for imposed_style in ("empathetic", "friendly", "headings", "JSON", "three sections"):
        assert imposed_style not in instructions
    assert snippet("customer-prompt").startswith("Hi!")
    assert "frustrated" in snippet("customer-prompt")


def test_pii_pair_changes_only_the_email():
    control = snippet("control-prompt")
    email = snippet("pii-prompt")
    assert email == control + "\nMy contact email is alex.customer@example.com."
    assert "@" not in control
    assert "repeat" not in email.lower()


def test_exact_native_evidence_and_retention_are_required():
    html = source().replace("<wbr>", "")
    for requirement in (
        "gpt-6.1-sol", "gpt-6-luna", "FW-GLM-5.3-Flash",
        "microsoft.foundry.content_filter.results",
        "source_type: prompt", "detected: true", "filtered: false",
        "filtered: true", "category", "Email",
        "not masking or anonymization", "Keep the default guardrail",
        "Leave the default controls unchanged", "Select only your",
        "remove any automatically attached tool",
        "Do not substitute a keyword blocklist",
        "Keep this agent for the next chapters", "original instructions are unchanged",
    ):
        assert requirement in html
    assert "Silver Lattice" not in html
    assert "stock_gap" not in html


def test_submitted_editorial_changes_remain_applied():
    html = source()
    creation = html.split('id="card-create-agent-1"', 1)[1].split("</article>", 1)[0]
    first_message = html.split('id="card-create-agent-2"', 1)[1].split("</article>", 1)[0]
    assert "Select your primary Sol deployment" in creation
    assert "Select your primary Sol deployment" not in first_message
    assert "<p>Start <strong>New chat</strong>. Send:</p>" in first_message
    for deleted in (
        "including recovery margin", 'id="conditional-evaluation"',
        "If either is already blocked", "an input control must detect the email",
        "refusal text alone is not proof", "If the trace or raw attribute is not visible",
        'id="ch-troubleshooting"', 'href="#ch-troubleshooting"',
        "Keep the conversation natural, the data synthetic, and the control observable.",
    ):
        assert deleted not in html
    assert "You created an agent, tried different models, enabled guardrails, and inspected traces." in html




def test_text_supplies_exact_portal_labels_without_ui_captures():
    html = source()
    for label in (
        "Sensitive data leakage", "PII (Preview)", "Email protection",
        "No models selected", "Trajectories", "Metadata",
    ):
        assert f"<strong>{label}</strong>" in html
    assert "Annotate and block" not in html
    assert "Next &rarr; Add agents" not in html
    assert "<img" not in html
    assert "Screenshot" not in html


def test_own_project_enables_tracing_before_guardrail_checks():
    html = source()
    setup = html.split('id="card-enable-tracing"', 1)[1].split("</article>", 1)[0]
    assert html.index('id="card-enable-tracing"') < html.index('id="card-create-agent-1"')
    for label in (
        "Agents", "Traces", "Connect", "Create new", "Application Insights",
        "Choose a connection", "Log Analytics Reader",
    ):
        assert f"<strong>{label}</strong>" in setup
    assert "Manage &rarr; Project details &rarr; Connected resources &rarr; Add connection" in setup
    for required in (
        "project traces page", "Lab 1 resource group", "Log Analytics workspace",
        "connection-success confirmation", "enables server-side tracing",
        "no SDK", "timestamp and response ID", "before the Block and Annotate comparison",
        "stop waiting after five minutes", "do not create multiple resources",
        "Do not change role assignments", "Privacy and cost",
    ):
        assert required in setup
    assert "select your own deployments, not centrally connected models" in html
    assert "Leave their final removal to the facilitator" in setup
    assert "trace-agent-setup" in html
    assert 'datetime="2026-10-01"' in html
    assert "Admin-connected" not in html
    assert "admin-connected" not in html


def test_lab_2_omits_the_removed_resume_reset_and_cleanup_section():
    html = source()
    assert 'id="resume-cleanup"' not in html
    assert "Resume, reset and cleanup" not in html
    assert "<strong>Reset this exercise:</strong>" not in html
