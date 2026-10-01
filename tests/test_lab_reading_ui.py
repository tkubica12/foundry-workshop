"""Exercise reading-only labs and the HTML-docs 1.2 appearance contract."""

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = [
    ROOT / "docs" / "index.html",
    *sorted((ROOT / "docs" / "guides").glob("*.html")),
    ROOT / "templates" / "lab-guide-template.html",
    ROOT / "templates" / "slide-deck-template.html",
]
GUIDES = sorted((ROOT / "docs" / "guides").glob("*.html"))
PAIRS = {
    "blue": ("#006da0", "#00a4ef"),
    "red": ("#bc3a16", "#f25022"),
    "green": ("#4c7100", "#7fba00"),
    "yellow": ("#805b00", "#ffb900"),
}


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as driver:
        instance = driver.chromium.launch()
        yield instance
        instance.close()


@pytest.mark.parametrize("document", [*GUIDES, ROOT / "templates" / "lab-guide-template.html"],
                         ids=lambda path: path.name)
def test_labs_have_no_presentation_or_sheet_surface(document):
    source = document.read_text(encoding="utf-8")
    for absent in (
        '<div class="slide-content', 'data-action="toggle-slides"',
        'data-action="toggle-sheet"', 'class="sheet',
        "html-docs/slides.css", "html-docs/slides.js", "html-docs/sheet.",
    ):
        assert absent not in source
    assert 'data-action="print"' in source


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: path.name)
def test_every_workshop_head_matches_the_installed_1_2_palette(document):
    source = document.read_text(encoding="utf-8")
    for pair in PAIRS.values():
        assert all(color in source for color in pair)
    assert "#0068bd" not in source
    assert "#69b8ff" not in source


@pytest.mark.parametrize("guide", GUIDES, ids=lambda path: path.name)
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_reading_query_deep_links_and_print_keep_the_lab_visible(browser, guide, theme):
    context = browser.new_context(color_scheme=theme, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(guide.as_uri() + "?view=slides#resume-cleanup")
        expect(page.locator("html")).not_to_have_attribute("data-view", "slides")
        expect(page.locator("#resume-cleanup")).to_be_visible()
        expect(page.locator("h1")).to_be_visible()
        assert page.locator(".slide-content").count() == 0
        page.evaluate("window.print = () => { window.printCalled = true; }")
        page.locator('[data-action="print"]').click()
        assert page.evaluate("window.printCalled")
        page.evaluate("dispatchEvent(new Event('beforeprint'))")
        expect(page.locator("html")).to_have_attribute("data-print", "read")
        page.emulate_media(media="print")
        assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()") == PAIRS["blue"][0]
        for body in page.locator(".card-body").all():
            expect(body).to_be_visible()
        page.evaluate("dispatchEvent(new Event('afterprint'))")
        expect(page.locator("html")).not_to_have_attribute("data-print", "read")
        assert not errors
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width,height", [(1280, 720), (1920, 1080), (390, 844)])
def test_lab_1_copy_controls_and_all_canonical_accents(browser, theme, width, height):
    context = browser.new_context(
        viewport={"width": width, "height": height}, color_scheme=theme,
        reduced_motion="reduce", offline=True,
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto((GUIDES[0]).as_uri())
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        page.locator('[data-action="expand-all"]').click()
        page.evaluate("""Object.defineProperty(navigator, "clipboard", {
          configurable: true, value: {writeText: async text => {window.copied = text;}}
        })""")
        page.locator("#hello-prompt [data-lab-copy]").click()
        prompt = page.locator("#hello-prompt code").inner_text()
        page.wait_for_function("(text) => window.copied === text", arg=prompt)
        for accent, pair in PAIRS.items():
            expect(page.locator("html")).to_have_attribute("data-accent", accent)
            assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()") == pair[theme == "dark"]
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.locator('[data-action="toggle-accent"]').click()
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-accent", "blue")
        assert not errors
    finally:
        context.close()
