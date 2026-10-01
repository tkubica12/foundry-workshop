"""Rendered contracts for the canonical HTML-docs reading experience."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS = REPO_ROOT / "docs" / "assets"
TEMPLATE = REPO_ROOT / "templates" / "lab-guide-template.html"
PUBLISHED = sorted(path for path in (REPO_ROOT / "docs").rglob("*.html")
                   if ".standalone." not in path.name)


@pytest.fixture(scope="module")
def rendered_page(tmp_path_factory):
    root = tmp_path_factory.mktemp("guide")
    shutil.copytree(ASSETS, root / "assets")
    (root / "guides").mkdir()
    page = root / "guides" / "guide.html"
    shutil.copyfile(TEMPLATE, page)
    return page.as_uri()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as driver:
        instance = driver.chromium.launch()
        yield instance
        instance.close()


def open_page(browser, url, *, width=1280, height=720, dark=False):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        color_scheme="dark" if dark else "light", reduced_motion="reduce",
    )
    context.route("https://**/*", lambda route: route.abort())
    context.route("http://**/*", lambda route: route.abort())
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text)
            if message.type in {"warning", "error"} else None)
    page.goto(url)
    page.wait_for_function("Boolean(window.HtmlDocs)")
    return context, page, errors


def test_template_cards_reveals_and_keyboard(browser, rendered_page):
    context, page, errors = open_page(browser, rendered_page)
    try:
        page.keyboard.press("Tab")
        expect(page.locator(".skip-link")).to_be_focused()
        page.locator('[data-action="expand-all"]').click()
        assert page.locator(".card[data-open]").count() == 3
        reveal = page.locator(".reveal-toggle")
        reveal.focus()
        page.keyboard.press("Enter")
        expect(page.locator(".reveal-body")).to_be_visible()
        expect(reveal).to_have_attribute("aria-expanded", "true")
        page.locator('[data-action="collapse-all"]').click()
        assert page.locator(".card[data-open]").count() == 0
        assert not errors
    finally:
        context.close()




@pytest.mark.parametrize("dark", [False, True], ids=["light", "dark"])
def test_chapter_2_text_steps_and_copy_work_on_mobile(browser, dark):
    guide = REPO_ROOT / "docs" / "guides" / "chapter-2-build-agent.html"
    context, page, errors = open_page(browser, guide.as_uri(), width=390, height=844, dark=dark)
    try:
        page.locator('[data-action="expand-all"]').click()
        assert page.locator("img").count() == 0
        assert "Guardrails" in page.locator("#card-guardrail-2").inner_text()
        assert "Trajectories" in page.locator("#card-decision-1").inner_text()
        tour = page.locator("#card-agent-channels")
        assert "Responses API" in tour.inner_text()
        assert "Agent2Agent (A2A)" in tour.inner_text()
        expect(tour.locator('a[href="#customer-prompt"]')).to_be_visible()
        page.evaluate("""Object.defineProperty(navigator, "clipboard", {
            configurable: true, value: {writeText: async text => {window.copied = text;}}
        })""")
        page.locator("#baseline-instructions [data-lab-copy]").click()
        expected = page.locator("#baseline-instructions code").inner_text()
        page.wait_for_function("(text) => window.copied === text", arg=expected)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors
    finally:
        context.close()


@pytest.mark.parametrize("viewport", ["1280x720", "1920x1080"])
def test_canonical_article_template_validator(rendered_page, viewport):
    node = shutil.which("node")
    assert node, "Node.js is required for the canonical HTML-docs validator."
    result = subprocess.run(
        [node, str(ASSETS / "html-docs" / "validate.js"),
         str(Path.from_uri(rendered_page)), "--viewport", viewport],
        text=True, capture_output=True, timeout=300, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all eight palettes" in result.stdout


@pytest.mark.parametrize("dark", [False, True], ids=["light", "dark"])
def test_template_theme_contrast_and_persistence(browser, rendered_page, dark):
    context, page, errors = open_page(browser, rendered_page, dark=dark)
    try:
        expect(page.locator("html")).to_have_attribute("data-theme", "dark" if dark else "light")
        ratio = page.evaluate("""() => {
          const luminance = value => {
            const c = value.match(/[\\d.]+/g).slice(0,3).map(Number).map(v => {
              v /= 255; return v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4;
            });
            return .2126*c[0]+.7152*c[1]+.0722*c[2];
          };
          const s = getComputedStyle(document.body);
          const a=luminance(s.color), b=luminance(s.backgroundColor);
          return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
        }""")
        assert ratio >= 7
        page.locator('[data-action="toggle-theme"]').click()
        page.locator('[data-action="toggle-accent"]').click()
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-theme", "light" if dark else "dark")
        expect(page.locator("html")).to_have_attribute("data-accent", "red")
        assert not errors
    finally:
        context.close()


def test_documents_keep_preferences_independent(browser):
    context, page, _ = open_page(browser, (REPO_ROOT / "docs" / "index.html").as_uri())
    try:
        page.locator('[data-action="toggle-theme"]').click()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.goto((REPO_ROOT / "docs" / "guides" / "chapter-2-build-agent.html").as_uri())
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        page.go_back()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    finally:
        context.close()


@pytest.mark.parametrize("document", PUBLISHED, ids=lambda path: path.name)
@pytest.mark.parametrize("dark", [False, True], ids=["light", "dark"])
@pytest.mark.parametrize("width,height", [(1920, 1080), (1280, 720), (390, 844)])
def test_published_page_layout_assets_and_console(browser, document, dark, width, height):
    context, page, errors = open_page(browser, document.as_uri(),
                                      width=width, height=height, dark=dark)
    try:
        expect(page.locator("h1").first).to_be_visible()
        if page.locator('[data-action="expand-all"]').count():
            page.locator('[data-action="expand-all"]').click()
        for image in page.locator("img").all():
            image.evaluate("image => { image.loading = 'eager'; }")
        page.wait_for_function("Array.from(document.images).every(i => i.complete)")
        assert page.evaluate("Array.from(document.images).every(i => i.naturalWidth > 0)")
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
        ), f"horizontal overflow in {document.name} at {width}x{height}"
        family = page.evaluate("getComputedStyle(document.body).fontFamily")
        assert "Segoe UI" in family
        assert not errors, f"{document.name}: {errors}"
    finally:
        context.close()


@pytest.mark.parametrize("document", PUBLISHED, ids=lambda path: path.name)
def test_published_reading_content_without_javascript(browser, document):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    try:
        page.goto(document.as_uri())
        expect(page.locator("h1").first).to_be_visible()
        if page.locator(".card-body").count():
            for body in page.locator(".card-body").all():
                expect(body).to_be_visible()
                assert body.inner_text().strip()
            for summary in page.locator(".slide-content").all():
                expect(summary).to_be_hidden()
        else:
            expect(page.locator("main")).to_be_visible()
            assert page.locator("main").inner_text().strip()
            for link in page.locator("main a").all():
                expect(link).to_be_visible()
    finally:
        context.close()
