"""Real browser journeys for the vendored, unmodified HTML-docs deck runtime."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]

BOUNDS_AUDIT_JS = """
slide => {
  const root = slide.getBoundingClientRect();
  const candidates = [...slide.querySelectorAll("*")].filter(node => {
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return !["SCRIPT", "STYLE"].includes(node.tagName)
      && style.visibility !== "hidden" && style.display !== "none"
      && parseFloat(style.opacity || "1") > 0
      && rect.width > 0 && rect.height > 0;
  });
  return candidates.flatMap(node => {
    const rect = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    const outside = rect.left < root.left - 1 || rect.top < root.top - 1
      || rect.right > root.right + 1 || rect.bottom > root.bottom + 1;
    const textBearing = [...node.childNodes].some(child =>
      child.nodeType === Node.TEXT_NODE && child.textContent.trim()
    );
    let zoom = 1;
    let clipped = false;
    for (let ancestor = node.parentElement; ancestor; ancestor = ancestor.parentElement) {
      const parentStyle = getComputedStyle(ancestor);
      if (ancestor === slide.parentElement) break;
      zoom *= parseFloat(parentStyle.zoom) || 1;
      const bounds = ancestor.getBoundingClientRect();
      const clipsX = /hidden|clip|auto|scroll/.test(parentStyle.overflowX);
      const clipsY = /hidden|clip|auto|scroll/.test(parentStyle.overflowY);
      clipped ||= (clipsX && (rect.left < bounds.left - 1 || rect.right > bounds.right + 1))
        || (clipsY && (rect.top < bounds.top - 1 || rect.bottom > bounds.bottom + 1));
    }
    const fontSize = parseFloat(style.fontSize) * zoom;
    const tooSmall = textBearing && fontSize < 17;
    const scrollClipped = (node.matches(".slide-body, pre")
      || (textBearing && /hidden|clip|auto|scroll/.test(style.overflowX + style.overflowY)))
      && (node.scrollWidth > node.clientWidth + 1 || node.scrollHeight > node.clientHeight + 1)
      && style.display !== "inline";
    return outside || tooSmall || clipped || scrollClipped
      ? [{tag: node.tagName, text: node.textContent.trim().slice(0, 80),
          outside, clipped, scrollClipped, fontSize}]
      : [];
  });
}
"""


@pytest.fixture(scope="module")
def deck_path(tmp_path_factory):
    root = tmp_path_factory.mktemp("deck")
    shutil.copytree(ROOT / "docs" / "assets", root / "assets")
    (root / "slides").mkdir()
    target = root / "slides" / "deck.html"
    shutil.copyfile(ROOT / "templates" / "slide-deck-template.html", target)
    return target


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as driver:
        instance = driver.chromium.launch()
        yield instance
        instance.close()


@pytest.mark.parametrize("viewport", ["1280x720", "1920x1080"])
def test_canonical_template_validator(deck_path, viewport):
    node = shutil.which("node")
    assert node, "Node.js is required for the canonical HTML-docs validator."
    result = subprocess.run(
        [node, str(ROOT / "docs" / "assets" / "html-docs" / "validate.js"),
         str(deck_path), "--viewport", viewport],
        text=True, capture_output=True, timeout=300, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all six palettes" in result.stdout


def test_keyboard_deeplink_click_fragments_and_focus(browser, deck_path):
    context = browser.new_context(reduced_motion="no-preference")
    page = context.new_page()
    try:
        page.goto(deck_path.as_uri())
        current = page.locator(".slide[data-current]")
        expect(current).to_have_attribute("id", "opening")
        page.locator("#opening").click(position={"x": 640, "y": 300})
        expect(current).to_have_attribute("id", "journey")
        page.keyboard.press("PageDown")
        expect(current).to_have_attribute("id", "evidence")
        expect(current).to_be_focused()
        page.keyboard.press("Space")
        expect(page.locator("#evidence .frag").first).to_have_attribute("data-shown", "")
        page.keyboard.press("End")
        expect(current).to_have_attribute("id", "closing")
        page.reload()
        expect(current).to_have_attribute("id", "closing")
        page.keyboard.press("Home")
        expect(current).to_have_attribute("id", "opening")
        page.keyboard.press("o")
        expect(page.get_by_role("dialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).to_be_hidden()
        expect(current).to_be_focused()
    finally:
        context.close()


@pytest.mark.parametrize("kind", ["figure", "container", "clipped-descendant", "tiny-text"])
def test_bounds_audit_rejects_oversized_non_text_visuals(browser, deck_path, kind):
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    try:
        page.goto(deck_path.as_uri())
        page.evaluate("""
            kind => {
              const node = document.createElement(kind === "figure" ? "figure" : "div");
              node.style.cssText =
                "position:absolute;left:1180px;top:200px;width:300px;height:180px;background:currentColor";
              if (kind === "figure") {
                const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
                svg.setAttribute("width", "300");
                svg.setAttribute("height", "180");
                node.append(svg);
              }
              if (kind === "clipped-descendant") {
                node.style.cssText = "position:absolute;left:200px;top:200px;width:100px;height:100px;overflow:hidden";
                const child = document.createElement("div");
                child.style.cssText = "width:300px;height:50px;background:currentColor";
                node.append(child);
              }
              if (kind === "tiny-text") {
                node.style.cssText = "position:absolute;left:200px;top:200px;font-size:12px";
                node.textContent = "Too small to project";
              }
              document.querySelector("#opening").append(node);
            }
        """, kind)
        violations = page.locator("#opening").evaluate(BOUNDS_AUDIT_JS)
        if kind == "clipped-descendant":
            assert any(item["clipped"] and not item["outside"] for item in violations)
        elif kind == "tiny-text":
            assert any(item["fontSize"] < 17 for item in violations)
        else:
            assert any(item["outside"] for item in violations)
            assert any(item["tag"] in {"FIGURE", "SVG", "DIV"} for item in violations)
    finally:
        context.close()


@pytest.mark.parametrize("slide", ["opening", "journey", "evidence", "closing"])
def test_template_slide_bounds(browser, deck_path, slide):
    context = browser.new_context(viewport={"width": 1280, "height": 720},
                                  reduced_motion="reduce")
    page = context.new_page()
    try:
        page.goto(deck_path.as_uri() + "#" + slide)
        expect(page.locator(".slide[data-current]")).to_have_attribute("id", slide)
        assert page.locator("#" + slide).evaluate(BOUNDS_AUDIT_JS) == []
    finally:
        context.close()


def test_trusted_fullscreen_transition(browser, deck_path):
    instance = browser.browser_type.launch(headless=False)
    page = instance.new_page()
    try:
        page.goto(deck_path.as_uri())
        page.get_by_role("button", name="Full screen", exact=True).click()
        page.wait_for_function("document.fullscreenElement !== null")
        page.keyboard.press("f")
        page.wait_for_function("document.fullscreenElement === null")
    finally:
        instance.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_no_javascript_deck_reflows_on_phone(browser, deck_path, theme):
    context = browser.new_context(
        java_script_enabled=False, viewport={"width": 390, "height": 844},
        color_scheme=theme,
    )
    page = context.new_page()
    try:
        authored = deck_path.with_name(f"deck-{theme}.html")
        authored.write_text(
            deck_path.read_text(encoding="utf-8").replace(
                'data-default-accent="blue"', f'data-default-accent="blue" data-default-theme="{theme}"'),
            encoding="utf-8",
        )
        page.goto(authored.as_uri())
        expected_bg = "rgb(16, 16, 16)" if theme == "dark" else "rgb(250, 250, 250)"
        assert page.evaluate("getComputedStyle(document.body).backgroundColor") == expected_bg
        assert page.locator(".slide:visible").count() == 5
        assert page.locator(".frag:visible").count() == 3
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        for slide in page.locator(".slide").all():
            assert slide.evaluate("el => el.scrollHeight <= el.clientHeight + 1")
        for node in page.locator(".slide-body, h1, .slide-title").all():
            assert float(node.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")) >= 18
    finally:
        context.close()
