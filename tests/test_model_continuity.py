"""Keep example deployments reusable without implying feature compatibility."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
GUIDES = sorted((ROOT / "docs" / "guides").glob("chapter-*.html"))


@pytest.mark.parametrize("guide", GUIDES[1:], ids=lambda path: path.name)
def test_later_labs_allow_existing_capacity_compatible_alternatives(guide):
    source = guide.read_text(encoding="utf-8")
    assert "gpt-6.1-sol" in source
    assert "another previously deployed" in source
    assert "capacity" in source
    assert "deployment name" in source
    assert "facilitator" in source
    for obsolete in ("Mistral-Large-3", "gpt-5.6-luna", "gpt-5.2"):
        assert obsolete not in source


def test_model_comparison_and_guardrail_path_have_distinct_requirements():
    source = GUIDES[1].read_text(encoding="utf-8")
    for required in (
        "gpt-6-luna", "FW-GLM-5.3-Flash",
        "not mandatory model IDs", "actual model ID, deployment name and version",
        "a different previously deployed model",
        "do not wait for a pending GLM deployment",
        "same-model rerun as a model comparison",
        "project-local deployment", "same guardrail-test deployment",
        "keep it unchanged through the Block and Annotate steps",
        "reuse it in Lab 3", "Record it as your guardrail-test deployment",
    ):
        assert required in source
    assert "do not substitute Lab 1's deployments" not in source


def test_evaluation_roles_and_capacity_restarts_preserve_comparability():
    for guide in (GUIDES[2], GUIDES[4]):
        source = guide.read_text(encoding="utf-8")
        assert "judge" in source
        assert "can differ from the agent model" in source
        assert "new baseline/candidate pair" in source
        assert "keep" in source.lower() and "unchanged" in source
    evaluation = GUIDES[2].read_text(encoding="utf-8")
    for required in (
        "judge deployment recorded in preflight",
        "Agent or judge compatibility alone does not prove generator support",
        "rubric-generation and scoring support separately",
        "record the compatible alternative for this separate evaluation",
    ):
        assert required in evaluation
    knowledge = GUIDES[4].read_text(encoding="utf-8")
    assert "planning and embedding deployments have separate compatibility requirements" in knowledge
    assert "do not replace them with Sol, Luna or GLM" in knowledge
    assert "text-embedding-3-small" in knowledge


def test_tool_model_is_confirmed_before_calls_and_recovery_repeats_checks():
    source = GUIDES[3].read_text(encoding="utf-8")
    assert "Keep your Lab 3 deployment" in source
    assert "confirms MCP/toolbox support" in source
    assert "before the first tool call" in source
    assert "Keep it unchanged throughout this lab" in source
    assert "repeat the affected checks" in source


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as driver:
        instance = driver.chromium.launch()
        yield instance
        instance.close()


@pytest.mark.parametrize("guide", GUIDES, ids=lambda path: path.name)
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width,height", [(390, 844), (1280, 720)])
def test_model_guidance_is_readable_offline(browser, guide, theme, width, height):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        color_scheme=theme, reduced_motion="reduce", offline=True,
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(guide.as_uri())
        page.locator('[data-action="expand-all"]').click()
        body = page.locator("main")
        expect(body).to_contain_text("previously deployed")
        expect(body).to_contain_text("capacity")
        expect(body).to_contain_text("deployment")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        assert not errors
    finally:
        context.close()
