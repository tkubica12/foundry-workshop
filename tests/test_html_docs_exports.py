"""Verify offline documents and the path-preserving navigable export collection."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

from test_docs_html import index_of

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RUNTIME = ROOT / "docs" / "assets" / "html-docs"
PAGES = sorted(p for p in DOCS.rglob("*.html") if ".standalone." not in p.name)
EXPORT_PATHS = {
    Path("index.html"),
    Path("guides/chapter-2-build-agent.html"),
    Path("guides/chapter-3-evaluate-agent.html"),
}


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as driver:
        instance = driver.chromium.launch()
        yield instance
        instance.close()


def run_node(*args):
    node = shutil.which("node")
    assert node, "Node.js is required for standalone export validation."
    result = subprocess.run([node, *map(str, args)], text=True, capture_output=True,
                            timeout=60, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_canonical_heads_match_vendored_source():
    run_node(RUNTIME / "sync-head.js", "--check", *PAGES,
             ROOT / "templates" / "lab-guide-template.html",
             ROOT / "templates" / "slide-deck-template.html")


@pytest.mark.parametrize("source", PAGES, ids=lambda p: str(p.relative_to(ROOT / "docs")))
def test_export_is_offline_and_keeps_reading_text(source, browser, tmp_path):
    target = tmp_path / source.name
    license_text = (RUNTIME / "LICENSE").read_text(encoding="utf-8").strip()
    assert license_text in source.read_text(encoding="utf-8"), "MIT notice must travel with export"
    run_node(RUNTIME / "bundle.js", source, target)
    assert list(tmp_path.iterdir()) == [target], "export isolation requires one HTML file only"
    assert license_text in target.read_text(encoding="utf-8")
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    try:
        page.goto(source.as_uri())
        selector = ".card-body" if page.locator(".card-body").count() else "main"
        original = page.locator(selector).all_inner_texts()
        assert original, "export must preserve actual reading content"
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        context.set_offline(True)
        page.goto(target.as_uri())
        assert page.locator(selector).all_inner_texts() == original
        assert page.locator(selector + ":visible").count() == len(original)
        assert all(url == target.as_uri() or url.startswith("data:") for url in requests)
        assert page.evaluate("Array.from(document.images).every(i => i.complete && i.naturalWidth)")
    finally:
        context.close()
    context = browser.new_context(offline=True, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(target.as_uri())
        expect(page.locator("h1").first).to_be_visible()
        page.locator('[data-action="toggle-theme"]').click()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        if page.locator('[data-action="toggle-slides"]').count():
            page.locator('[data-action="toggle-slides"]').click()
            page.keyboard.press("End")
            expect(page.locator("[data-slide-current]")).to_have_attribute("id", "closing")
        assert not errors
    finally:
        context.close()


@pytest.fixture(scope="module")
def export_collection(tmp_path_factory):
    root = tmp_path_factory.mktemp("workshop-exports")
    assert {source.relative_to(DOCS) for source in PAGES} == EXPORT_PATHS
    for source in PAGES:
        target = root / source.relative_to(DOCS)
        target.parent.mkdir(parents=True, exist_ok=True)
        run_node(RUNTIME / "bundle.js", source, target)
    assert {path.relative_to(root) for path in root.rglob("*") if path.is_file()} == EXPORT_PATHS
    return root


@pytest.mark.parametrize("javascript", [True, False], ids=["interactive", "no-javascript"])
def test_export_collection_preserves_companion_navigation(export_collection, browser, javascript):
    context = browser.new_context(java_script_enabled=javascript, offline=True,
                                  reduced_motion="reduce")
    page = context.new_page()
    errors, failures = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("requestfailed", lambda request: failures.append(request.url))
    try:
        for relative in sorted(EXPORT_PATHS):
            document = export_collection / relative
            for href in set(index_of(document).links):
                parsed = urlsplit(href)
                if parsed.scheme or not parsed.path.lower().endswith(".html"):
                    continue
                target = (document.parent / unquote(parsed.path)).resolve()
                assert target.is_relative_to(export_collection), href
                assert target.relative_to(export_collection) in EXPORT_PATHS, href
                assert target.is_file(), href
                if parsed.fragment:
                    assert unquote(parsed.fragment) in index_of(target).ids, href
                page.goto(document.as_uri())
                if javascript and page.locator('[data-action="expand-all"]').count():
                    page.locator('[data-action="expand-all"]').click()
                link = page.locator("a").evaluate_all(
                    "(links, href) => links.findIndex(link => link.getAttribute('href') === href)",
                    href,
                )
                assert link >= 0, href
                page.locator("a").nth(link).click()
                expect(page).to_have_url(target.as_uri() + ("#" + parsed.fragment if parsed.fragment else ""))
                expect(page.locator("h1").first).to_be_visible()
        assert not errors
        assert not failures
    finally:
        context.close()
