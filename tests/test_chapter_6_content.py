"""Protect the controlled no-memory/profile/summary comparison."""

from pathlib import Path
from html.parser import HTMLParser

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guides" / "chapter-6-managed-memory.html"
INPUTS = {
    "agent-instructions": "Answer briefly in the language of the user. Use the current conversation and available memory tools for personal facts and previous discussions. If evidence is missing, say you do not know. Do not invent preferences or past conversations.",
    "seed-prompt": "Remember that I like apples. Today we discussed a fruit snack for a fictional hiking trip: pack apples in a reusable box.",
    "baseline-prompt": "What fruit do I like? Have we ever discussed fruit?",
    "profile-prompt": "What fruit do I like?",
    "summary-prompt": "Have we ever discussed fruit? What did we plan for the fictional hiking snack, and how were we going to pack it?",
}


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def test_memory_comparison_keeps_scope_evidence_and_cleanup_boundaries():
    source = GUIDE.read_text(encoding="utf-8")
    parser = TextOnly()
    parser.feed(source[source.index("<body>"):])
    text = " ".join(" ".join(parser.parts).split())
    for fragment in (
        "{{$userId}}", "user_profile", "chat_summary", "30 seconds",
        "after attachment", "same signed-in identity", "New chat",
        "apples and the reusable box", "Do not manufacture a row",
        "Never delete a shared store", "platform logs",
        "Procedural memory", "1 October 2026",
    ):
        assert fragment in text
    assert text.index("Try without memory /") < text.index("Enable managed memory /")
    assert "apples" not in INPUTS["agent-instructions"]
    assert "apples" not in INPUTS["profile-prompt"]
    assert "reusable box" not in INPUTS["summary-prompt"]


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [(1280, 720), (390, 844)])
def test_memory_lab_copy_controls_and_layout(theme, viewport):
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context(
            offline=True, color_scheme=theme, reduced_motion="reduce",
            viewport={"width": viewport[0], "height": viewport[1]},
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(GUIDE.as_uri())
            page.locator('[data-action="expand-all"]').click()
            page.evaluate("""Object.defineProperty(navigator, "clipboard", {
                configurable: true,
                value: {writeText: async text => {window.copied = text;}}
            })""")
            for block_id, expected in INPUTS.items():
                assert page.locator(f"#{block_id} code").inner_text() == expected
                page.locator(f"#{block_id} [data-lab-copy]").click()
                page.wait_for_function("(text) => window.copied === text", arg=expected)
                assert "copied" in page.locator(f"#{block_id} [role=status]").inner_text()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors
        finally:
            context.close()
            browser.close()
