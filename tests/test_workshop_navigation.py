"""Verify the published entry points using real loopback browser navigation."""

from __future__ import annotations

import functools
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

from test_docs_html import index_of

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
EVIDENCE = REPO_ROOT / "evidence" / "ui-navigation"
ENTRY_POINTS = {
    "guides/chapter-2-build-agent.html": "Lab 2: Build an agent",
    "guides/chapter-3-evaluate-agent.html": "Lab 3: Evaluate and improve",
}


@pytest.fixture(scope="module")
def site():
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(DOCS))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive(), "loopback preview did not stop"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as driver:
        instance = driver.chromium.launch()
        yield instance
        instance.close()


def local_target(document: Path, href: str) -> Path:
    parsed = urlsplit(href)
    path = (document.parent / unquote(parsed.path)).resolve() if parsed.path else document
    assert path.is_relative_to(DOCS), f"published link leaves the docs tree: {href}"
    assert path.is_file(), f"missing published target: {href}"
    if parsed.fragment:
        assert unquote(parsed.fragment) in index_of(path).ids, f"missing anchor: {href}"
    return path


def test_index_publishes_exactly_the_implemented_entry_points():
    index = index_of(DOCS / "index.html")
    links = {href for href in index.links if not href.startswith("#")}
    assert links == set(ENTRY_POINTS)
    for href in links:
        local_target(DOCS / "index.html", href)
    assert {"labs", "up-next"} <= index.ids
    assert set(path.relative_to(DOCS).as_posix() for path in DOCS.rglob("*.html")) == {
        "index.html", *ENTRY_POINTS,
    }


def test_future_labs_are_named_without_dead_links():
    text = (DOCS / "index.html").read_text(encoding="utf-8")
    assert "Lab 4: Tools" in text
    assert "Lab 5: Knowledge" in text
    assert "These labs are not available yet." in text
    assert 'data-action="toggle-slides"' not in text
    assert 'data-action="expand-all"' not in text
    assert ".workshop" not in text


def test_chapter_2_card_duration_matches_the_guide():
    guide = (DOCS / "guides" / "chapter-2-build-agent.html").read_text(encoding="utf-8")
    duration = re.findall(r"<strong>Time</strong>\s*(\d+)\s+minutes", guide)
    assert len(duration) == 1, "Chapter 2 guide must declare one total duration"
    card = re.search(
        r'<a href="guides/chapter-2-build-agent\.html">.*?</li>',
        (DOCS / "index.html").read_text(encoding="utf-8"),
        flags=re.DOTALL,
    )
    assert card, "Chapter 2 must have a linked index card"
    assert re.findall(r"(\d+)\s+minutes", card.group()) == duration, (
        "Chapter 2 index duration must match the guide's declared total"
    )


def test_all_published_local_links_and_assets_are_served(site, browser):
    context = browser.new_context()
    try:
        checked: set[str] = set()
        for document in sorted(DOCS.rglob("*.html")):
            parsed = index_of(document)
            hrefs = [*parsed.links, *parsed.assets, *(image["src"] for image in parsed.images)]
            for href in hrefs:
                if urlsplit(href).scheme or href.startswith("//"):
                    continue
                target = local_target(document, href)
                url = urljoin(site, target.relative_to(DOCS).as_posix())
                if url not in checked:
                    response = context.request.get(url)
                    assert response.status == 200, f"{url}: HTTP {response.status}"
                    assert response.body(), f"{url}: empty response"
                    checked.add(url)
        assert len(checked) >= len(ENTRY_POINTS) + 1
        for private_path in (
            ".git/config", ".env", ".workshop/chapter-2/state.json",
            ".workshop/archive/2026-09-18-labs-first/PLAN.md",
            "slides/index.html", "guides/evaluation-and-operations.html",
        ):
            assert context.request.get(urljoin(site, private_path)).status == 404
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width,height", [(1280, 720), (390, 844)])
def test_actual_index_to_every_active_guide_journey(site, browser, theme, width, height):
    context = browser.new_context(
        viewport={"width": width, "height": height}, color_scheme=theme,
        reduced_motion="reduce",
    )
    external: list[str] = []

    def local_only(route):
        if route.request.url.startswith(site):
            route.continue_()
        else:
            external.append(route.request.url)
            route.abort()

    context.route("**/*", local_only)
    page = context.new_page()
    errors: list[str] = []
    failures: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("requestfailed", lambda request: failures.append(request.url))
    try:
        page.goto(site)
        page.wait_for_function("Boolean(window.HtmlDocs)")
        assert page.locator("html").get_attribute("data-theme") == theme
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(EVIDENCE / f"index-{width}-{theme}.png"), full_page=True)
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
        )
        for href, label in ENTRY_POINTS.items():
            link = page.get_by_role("link", name=label, exact=True)
            expect(link).to_have_attribute("href", href)
            link.click()
            expect(page).to_have_url(urljoin(site, href))
            expect(page.locator("h1")).to_be_visible()
            page.go_back()
            expect(page).to_have_url(site)
        assert not external, f"external runtime requests: {external}"
        assert not errors, f"browser errors: {errors}"
        assert not failures, f"failed requests: {failures}"
    finally:
        context.close()


def test_keyboard_navigation_theme_persistence_and_deep_link(site, browser):
    context = browser.new_context(color_scheme="light", reduced_motion="reduce")
    page = context.new_page()
    try:
        page.goto(site)
        page.keyboard.press("Tab")
        expect(page.locator(".skip-link")).to_be_focused()
        page.keyboard.press("Enter")
        expect(page).to_have_url(site + "#content")
        theme = page.locator('[data-action="toggle-theme"]')
        theme.focus()
        page.keyboard.press("Enter")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.goto(site + "#up-next")
        page.reload()
        expect(page.locator("#up-next")).to_be_in_viewport()
        link = page.get_by_role("link", name="Lab 2: Build an agent", exact=True)
        link.focus()
        page.keyboard.press("Enter")
        expect(page).to_have_url(urljoin(site, "guides/chapter-2-build-agent.html"))
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        page.go_back()
        expect(page).to_have_url(site + "#up-next")
    finally:
        context.close()


@pytest.mark.parametrize("origin", ["file", "http"])
def test_index_remains_navigable_without_javascript(origin, site, browser):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    url = (DOCS / "index.html").as_uri() if origin == "file" else site
    try:
        page.goto(url)
        for href, label in ENTRY_POINTS.items():
            page.get_by_role("link", name=label, exact=True).click()
            expect(page).to_have_url(urljoin(url, href))
            expect(page.locator("h1")).to_be_visible()
            page.go_back()
            expect(page).to_have_url(url)
    finally:
        context.close()
