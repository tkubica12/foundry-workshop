"""Real-browser journeys for the local-only attendee learning passport."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

REPO_ROOT = Path(__file__).resolve().parents[1]
PASSPORT = REPO_ROOT / "docs" / "guides" / "learning-passport.html"
LAB = REPO_ROOT / "docs" / "guides" / "chapter-2-build-agent.html"


def wait_for_passport(page) -> None:
    page.wait_for_selector('#card-checkpoint-c1 .card-toggle[aria-controls="checkpoint-c1"]')
    page.wait_for_function(
        "!document.querySelector('[data-save-status]').textContent.startsWith('JavaScript is unavailable.')"
    )


@pytest.fixture(scope="module")
def browser():
    with playwright_api.sync_playwright() as driver:
        browser = driver.chromium.launch()
        yield browser
        browser.close()


def open_page(browser, *, width: int = 1280, height: int = 720, storage_denied: bool = False, expand: bool = True):
    context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
    if storage_denied:
        context.add_init_script(
            """
            Object.defineProperty(Storage.prototype, 'getItem', {value() { throw new DOMException('denied'); }});
            Object.defineProperty(Storage.prototype, 'setItem', {value() { throw new DOMException('denied'); }});
            Object.defineProperty(Storage.prototype, 'removeItem', {value() { throw new DOMException('denied'); }});
            """
        )
    page = context.new_page()
    requests: list[str] = []
    errors: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(PASSPORT.as_uri())
    wait_for_passport(page)
    if expand:
        page.locator('[data-action="expand-all"]').click()
    return context, page, requests, errors


def complete_release_evidence(page) -> None:
    values = {
        "c4.baselineEvaluationId": "eval-baseline-07",
        "c4.candidateEvaluationId": "eval-candidate-07",
        "c4.traceIds": "trace-e01, trace-e06",
        "c4.instructionsHash": "sha256-instructions",
        "c4.modelRoute": "synthetic-route@1",
        "c4.sourceSetHash": "sha256-sources",
        "c4.toolSetHash": "none",
        "c4.policyHash": "sha256-policy",
        "c4.effectiveIdentity": "evaluation-principal-E",
        "c4.parameters": "temperature=0; max_output_tokens=600",
        "c5.developmentRunId": "run-development-07",
        "c5.holdoutRunId": "run-holdout-07",
        "c5.developmentPasses": "8",
        "c5.developmentAttempted": "8",
        "c5.developmentIncomplete": "0",
        "c5.developmentTimedOut": "0",
        "c5.developmentAccessBlocked": "0",
        "c5.holdoutPasses": "4",
        "c5.holdoutAttempted": "4",
        "c5.holdoutIncomplete": "0",
        "c5.holdoutTimedOut": "0",
        "c5.holdoutAccessBlocked": "0",
        "c5.criticalResult": "pass",
        "c5.regressionResult": "none",
        "c5.operationalEvidence": "n=12; latency 1.1-1.8s; tokens recorded",
        "c5.operationalResult": "pass",
        "c5.authorizationEvidence": "T02-run-07; T03-run-07; service boundary"
    }
    for name, value in values.items():
        page.locator(f'[name="{name}"]').fill(value)
    page.locator('[name="c4.evidenceSubject"]').select_option("own-candidate")
    page.locator('[name="c5.authorizationStatus"]').select_option("proven")
    page.locator('[name="c5.ownDecision"]').select_option(label="release")
    page.wait_for_function("document.querySelector('[data-fingerprint-output]').value.length > 20")


def test_actual_input_refresh_export_import_and_reset_journey(browser, tmp_path: Path) -> None:
    context, page, requests, errors = open_page(browser)
    try:
        page.locator('[name="meta.seatLabel"]').fill("seat-07")
        page.locator('[name="c2.agentName"]').fill("stock-agent-seat-07")
        page.locator('[name="capstone.parentVersion"]').fill("stock-agent-seat-07@c4")
        page.reload()
        wait_for_passport(page)
        page.locator('[data-action="expand-all"]').click()
        assert page.locator('[name="c2.agentName"]').input_value() == "stock-agent-seat-07"

        complete_release_evidence(page)
        own_fingerprint = page.locator('[data-fingerprint-output]').input_value()
        assert own_fingerprint.startswith(("sha256-", "fnv1a-"))
        assert "Effective outcome: release." in page.locator("[data-decision-status]").inner_text()

        with page.expect_download() as download_info:
            page.locator("[data-export]").click()
        export_path = tmp_path / "passport.json"
        download_info.value.save_as(export_path)
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        assert payload["state"]["c4.candidateFingerprint"] == own_fingerprint
        assert "<script" not in json.dumps(payload).lower()

        page.on("dialog", lambda dialog: dialog.accept())
        page.locator("[data-reset]").click()
        assert page.locator('[name="c2.agentName"]').input_value() == ""
        page.locator("[data-import-input]").set_input_files(export_path)
        page.wait_for_function(
            "document.querySelector('[name=\"c2.agentName\"]').value === 'stock-agent-seat-07'"
        )
        assert page.locator('[name="c2.agentName"]').input_value() == "stock-agent-seat-07"
        assert "Import complete" in page.locator("[data-save-status]").inner_text()
        assert errors == []
        assert all(url.startswith("file:") for url in requests)
    finally:
        context.close()


def test_release_with_missing_evidence_becomes_insufficient(browser) -> None:
    context, page, _, _ = open_page(browser)
    try:
        page.locator('[name="c5.ownDecision"]').select_option(label="release")
        assert "insufficient evidence" in page.locator("[data-decision-status]").inner_text().lower()
    finally:
        context.close()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("c5.developmentPasses", "6"),
        ("c5.holdoutPasses", "2"),
        ("c5.developmentAttempted", "7"),
        ("c5.holdoutAttempted", "3"),
        ("c5.developmentIncomplete", "1"),
        ("c5.holdoutTimedOut", "1"),
        ("c5.developmentAccessBlocked", "1"),
        ("c5.criticalResult", "fail"),
        ("c5.regressionResult", "found"),
        ("c5.operationalResult", "insufficient evidence"),
    ],
)
def test_release_gate_rejects_failed_or_unknown_evidence(browser, field: str, value: str) -> None:
    context, page, _, _ = open_page(browser)
    try:
        complete_release_evidence(page)
        page.locator(f'[name="{field}"]').fill(value)
        assert "insufficient evidence" in page.locator("[data-decision-status]").inner_text().lower()
    finally:
        context.close()


@pytest.mark.parametrize("status", ["failed", "not-tested", "partial", ""])
def test_release_gate_requires_exact_authorization_proof(browser, status: str) -> None:
    context, page, _, _ = open_page(browser)
    try:
        complete_release_evidence(page)
        page.locator('[name="c5.authorizationStatus"]').select_option(status)
        assert "insufficient evidence" in page.locator("[data-decision-status]").inner_text().lower()
    finally:
        context.close()


@pytest.mark.parametrize(
    ("status", "evidence"),
    [
        ("not-tested", "not proven"),
        ("partial", "T02 proven, T03 failed"),
        ("not-tested", "cannot be proven without environment"),
        ("not-tested", "no evidence"),
        ("not-tested", "unproven"),
    ],
)
def test_negated_or_partial_proof_text_cannot_override_status(
    browser, status: str, evidence: str
) -> None:
    context, page, _, _ = open_page(browser)
    try:
        complete_release_evidence(page)
        page.locator('[name="c5.authorizationStatus"]').select_option(status)
        page.locator('[name="c5.authorizationEvidence"]').fill(evidence)
        assert "insufficient evidence" in page.locator("[data-decision-status]").inner_text().lower()
    finally:
        context.close()


def test_reference_evidence_cannot_release_own_candidate(browser) -> None:
    context, page, _, _ = open_page(browser)
    try:
        complete_release_evidence(page)
        page.locator('[name="c4.evidenceSubject"]').select_option("supplied-reference")
        assert "insufficient evidence" in page.locator("[data-decision-status]").inner_text().lower()
    finally:
        context.close()


def test_fingerprint_stays_blank_until_configuration_is_complete(browser) -> None:
    context, page, _, _ = open_page(browser)
    try:
        page.locator('[name="c4.modelRoute"]').fill("route-a@1")
        assert page.locator("[data-fingerprint-output]").input_value() == ""
        complete_release_evidence(page)
        assert page.locator("[data-fingerprint-output]").input_value()
        page.locator('[name="c4.effectiveIdentity"]').fill("")
        assert page.locator("[data-fingerprint-output]").input_value() == ""
        assert "insufficient evidence" in page.locator("[data-decision-status]").inner_text().lower()
    finally:
        context.close()


def test_own_and_reference_decisions_remain_separate(browser) -> None:
    context, page, _, _ = open_page(browser)
    try:
        page.locator('[name="c4.ownDecision"]').select_option(label="do not release")
        page.locator('[name="c4.referenceDecision"]').select_option(label="release")
        assert page.locator('[name="c4.ownDecision"]').input_value() == "do not release"
        assert page.locator('[name="c4.referenceDecision"]').input_value() == "release"
    finally:
        context.close()


def test_candidate_fingerprint_changes_with_configuration(browser) -> None:
    context, page, _, _ = open_page(browser)
    try:
        complete_release_evidence(page)
        first = page.locator("[data-fingerprint-output]").input_value()
        page.locator('[name="c4.modelRoute"]').fill("route-b@1")
        page.wait_for_function(
            "(before) => document.querySelector('[data-fingerprint-output]').value !== before",
            arg=first,
        )
        assert page.locator("[data-fingerprint-output]").input_value() != first
    finally:
        context.close()


def test_storage_denial_keeps_current_page_usable(browser) -> None:
    context, page, _, errors = open_page(browser, storage_denied=True)
    try:
        page.locator('[name="c2.agentName"]').fill("still-usable")
        assert page.locator('[name="c2.agentName"]').input_value() == "still-usable"
        assert "storage" in page.locator("[data-save-status]").inner_text().lower()
        with page.expect_download() as download_info:
            page.locator("[data-export]").click()
        assert download_info.value.suggested_filename.startswith("learning-passport-")
        assert errors == []
    finally:
        context.close()


def test_malformed_import_fails_visibly_and_does_not_execute_markup(browser, tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"schemaVersion":1,"state":"<script>window.evil=true</script>"}', encoding="utf-8")
    context, page, _, errors = open_page(browser)
    try:
        page.locator("[data-import-input]").set_input_files(malformed)
        page.wait_for_function(
            "document.querySelector('[data-save-status]').textContent.includes('Import failed')"
        )
        assert "Import failed" in page.locator("[data-save-status]").inner_text()
        assert page.evaluate("window.evil") is None
        assert errors == []
    finally:
        context.close()


def test_imported_markup_is_inert_text(browser, tmp_path: Path) -> None:
    payload = tmp_path / "markup.json"
    payload.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "state": {"c2.agentName": "<img src=x onerror='window.evil=true'>"},
            }
        ),
        encoding="utf-8",
    )
    context, page, _, errors = open_page(browser)
    try:
        page.locator("[data-import-input]").set_input_files(payload)
        page.wait_for_function(
            "document.querySelector('[data-save-status]').textContent.includes('Import complete')"
        )
        assert page.locator('[name="c2.agentName"]').input_value().startswith("<img")
        assert page.evaluate("window.evil") is None
        assert errors == []
    finally:
        context.close()


@pytest.mark.parametrize(
    ("width", "height", "theme"),
    [(1440, 1000, "light"), (390, 844, "dark")],
    ids=["wide-light", "narrow-dark"],
)
def test_layout_theme_and_screenshot(browser, tmp_path: Path, width: int, height: int, theme: str) -> None:
    context, page, _, errors = open_page(browser, width=width, height=height)
    try:
        if page.evaluate("document.documentElement.dataset.theme") != theme:
            page.locator('[data-action="toggle-theme"]').click()
        assert page.evaluate("document.documentElement.dataset.theme") == theme
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1
        page.screenshot(path=tmp_path / f"passport-{width}-{theme}.png", full_page=True)
        assert errors == []
    finally:
        context.close()


def test_no_javascript_keeps_core_readable_and_printable(browser) -> None:
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    try:
        page.goto(PASSPORT.as_uri())
        assert page.locator("h1").is_visible()
        assert page.locator("#checkpoint-c1").is_visible()
        assert page.locator("#checkpoint-c5").is_visible()
        assert page.locator(".noscript-note").is_visible()
    finally:
        context.close()


def test_arrival_opens_first_working_fields_without_a_disclosure_click(browser) -> None:
    context, page, _, errors = open_page(browser, expand=False)
    try:
        assert page.locator(".card[data-open]").count() == 1
        assert page.locator("#card-checkpoint-c1 > .card-body").is_visible()
        assert page.locator('[name="meta.seatLabel"]').is_visible()
        page.locator('[name="meta.seatLabel"]').fill("seat-09")
        assert page.locator('[name="meta.seatLabel"]').input_value() == "seat-09"
        assert page.locator("[data-export]").is_visible()
        assert page.locator('[data-action="toggle-slides"]').count() == 0
        assert errors == []
    finally:
        context.close()


@pytest.mark.parametrize(
    "anchor",
    ["checkpoint-c1", "checkpoint-c2", "checkpoint-c3", "checkpoint-c4",
     "capstone-lineage", "checkpoint-c5", "privacy", "c4-heading",
     "parameters", "authorization-status", "decision-limit"],
)
def test_passport_legacy_links_open_the_containing_card(browser, anchor: str) -> None:
    context, page, _, errors = open_page(browser, expand=False)
    try:
        page.goto(PASSPORT.as_uri() + "#" + anchor)
        target = page.locator("#" + anchor)
        assert target.is_visible()
        card = target.locator("xpath=ancestor::article[contains(@class, 'card')]")
        assert card.get_attribute("data-open") is not None
        assert card.locator(".card-toggle").get_attribute("aria-expanded") == "true"
        assert errors == []
    finally:
        context.close()


def test_canonical_appearance_persists_without_changing_passport_data(browser) -> None:
    context, page, _, errors = open_page(browser, expand=False)
    try:
        page.locator('[name="meta.seatLabel"]').fill("seat-12")
        saved = json.loads(page.evaluate("localStorage.getItem('foundry-learning-passport-v1')"))
        previous = page.locator("html").get_attribute("data-theme")
        page.locator('[data-action="toggle-theme"]').click()
        changed = page.locator("html").get_attribute("data-theme")
        assert changed != previous
        page.locator('[data-action="toggle-accent"]').click()
        assert page.locator("html").get_attribute("data-accent") == "orange"
        page.reload()
        assert page.locator("html").get_attribute("data-theme") == changed
        assert page.locator("html").get_attribute("data-accent") == "orange"
        restored = json.loads(page.evaluate("localStorage.getItem('foundry-learning-passport-v1')"))
        assert restored["schemaVersion"] == saved["schemaVersion"]
        assert restored["state"] == saved["state"]
        assert page.locator('[name="meta.seatLabel"]').input_value() == "seat-12"
        assert errors == []
    finally:
        context.close()


@pytest.mark.parametrize(
    "field",
    ["c4.instructionsHash", "c4.modelRoute", "c4.sourceSetHash", "c4.toolSetHash",
     "c4.policyHash", "c4.effectiveIdentity", "c4.parameters"],
)
def test_every_configuration_field_remains_part_of_fingerprint_and_release_gate(browser, field: str) -> None:
    context, page, _, errors = open_page(browser)
    try:
        complete_release_evidence(page)
        original = page.locator("[data-fingerprint-output]").input_value()
        page.locator(f'[name="{field}"]').fill("changed-inspected-value")
        page.wait_for_function(
            "(before) => document.querySelector('[data-fingerprint-output]').value !== before",
            arg=original,
        )
        page.locator(f'[name="{field}"]').fill("")
        assert page.locator("[data-fingerprint-output]").input_value() == ""
        assert page.locator("[data-decision-status]").get_attribute("data-outcome") == "insufficient"
        assert errors == []
    finally:
        context.close()


def test_lab_preflight_legacy_links_and_exact_copy_feedback(browser) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(LAB.as_uri())
        assert page.locator("#before-you-start").is_visible()
        assert page.locator("#card-before-you-start-1 .card-toggle").get_attribute("aria-expanded") == "true"
        assert page.locator(".card[data-open]").count() == 1
        for anchor in ["create-agent", "model-choice", "guardrail", "decision"]:
            page.goto(LAB.as_uri() + "#" + anchor)
            assert page.locator("#" + anchor).is_visible()
        page.locator('[data-action="expand-all"]').click()
        page.evaluate("""
            Object.defineProperty(navigator, "clipboard", {
                configurable: true,
                value: {writeText: async text => {window.copiedLabInput = text;}}
            });
        """)
        for block in page.locator(".code").all():
            expected = block.locator("pre > code").text_content()
            label = block.locator(".code-label").inner_text()
            button = block.locator("[data-lab-copy]")
            assert button.get_attribute("aria-label") == "Copy " + label
            button.click()
            assert page.evaluate("window.copiedLabInput") == expected
            assert block.locator(".lab-copy-status").inner_text() == label + " copied."
        page.evaluate("""
            Object.defineProperty(navigator, "clipboard", {
                configurable: true,
                value: {writeText: async () => {throw new DOMException("denied");}}
            });
        """)
        block = page.locator(".code").first
        block.locator("[data-lab-copy]").click()
        assert "Copy unavailable" in block.locator(".lab-copy-status").inner_text()
        assert "Ctrl+C" in block.locator(".lab-copy-status").inner_text()
        assert page.evaluate("getSelection().toString()") == block.locator("pre > code").text_content()
        assert errors == []
    finally:
        context.close()


@pytest.mark.parametrize("javascript", [True, False], ids=["interactive", "no-javascript"])
def test_lab_readiness_gate_and_continuation_stay_explicit(browser, javascript: bool) -> None:
    context = browser.new_context(java_script_enabled=javascript, reduced_motion="reduce")
    page = context.new_page()
    try:
        page.goto(LAB.as_uri())
        readiness = page.locator("#prepared-seat-readiness")
        assert readiness.is_visible()
        gate = " ".join(readiness.inner_text().split())
        assert "Confirm with your facilitator" in gate
        assert "create agents and personal-information guardrails" in gate
        assert "select the models below, and read traces" in gate
        assert "If sign-in or a required control is unavailable, stop and contact your facilitator" in gate
        assert "do not switch to a personal account or deploy replacements" in gate
        assert page.locator(".lab-meta").inner_text().split("Time", 1)[1].lstrip().startswith("30 minutes")

        if javascript:
            page.locator('[data-action="expand-all"]').click()
        continuation = page.locator("#card-decision-2 .card-body")
        assert continuation.is_visible()
        text = " ".join(continuation.inner_text().split())
        assert "original instructions" in text
        assert "Keep the agent on gpt-5.2 with your lab-only Annotate policy" in text
        assert "Keep model, policy and knowledge fixed during that comparison" in text
        assert "improvement must be measured, not assumed" in text
        assert continuation.locator("a").get_attribute("href") == "learning-passport.html#checkpoint-c2"
        assert "extension fields are not required for Labs 2 and 3" in text
    finally:
        context.close()
