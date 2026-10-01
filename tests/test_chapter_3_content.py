"""Check the local evaluation-lab journey without claiming a native Foundry run."""

import base64
import json
import re
import subprocess
from html import unescape
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guides" / "chapter-3-evaluate-agent.html"
INPUTS = ROOT / "student" / "labs" / "evaluate-agent"


def snippet(identifier):
    match = re.search(
        rf'<div class="code" id="{identifier}">.*?<code>(.*?)</code>',
        GUIDE.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    assert match, f"Missing copyable input: {identifier}"
    return unescape(match.group(1))


@pytest.mark.parametrize(
    "identifier,filename",
    [
        ("evaluation-dataset", "pickup-style-v1.jsonl"),
        ("style-rubric", "casual-style-rubric.txt"),
        ("candidate-instructions", "candidate-instructions.txt"),
    ],
)
def test_copyable_inputs_match_authoritative_files(identifier, filename):
    assert snippet(identifier) + "\n" == (INPUTS / filename).read_text(encoding="utf-8")


def test_dataset_has_eight_distinct_natural_inputs_not_old_answers():
    rows = [json.loads(line) for line in snippet("evaluation-dataset").splitlines()]
    assert len(rows) == 8
    assert len({row["query"] for row in rows}) == 8
    for row in rows:
        assert set(row) == {"query"}
        assert "fictional training case" not in row["query"].lower()
        assert "synthetic" not in row["query"].lower()
        assert "evaluation" not in row["query"].lower()
        assert "@" not in row["query"]
    assert any("frustrated" in row["query"] for row in rows)
    assert any("thank" in row["query"].lower() for row in rows)
    assert any("estimated completion time" in row["query"] for row in rows)
    assert any("change the pickup store" in row["query"] for row in rows)


def test_candidate_keeps_original_scope_and_adds_only_behavior_instructions():
    prior = (ROOT / "docs" / "guides" / "chapter-2-build-agent.html").read_text(encoding="utf-8")
    original = re.search(
        r'id="baseline-instructions".*?<code>(.*?)</code>', prior, re.DOTALL
    )
    assert original
    assert snippet("candidate-instructions").startswith(unescape(original.group(1)) + "\n\n")
    assert "70 words" in snippet("candidate-instructions")
    assert "frustration" in snippet("candidate-instructions")


def test_judge_schema_and_fair_comparison_are_explicit():
    rubric = snippet("style-rubric")
    assert "{{query}}" in rubric and "{{response}}" in rubric
    output = json.loads(re.search(r'(\{"result":.*\})', rubric).group(1))
    assert set(output) == {"result", "reason"}
    assert type(output["result"]) is int
    for score in range(1, 6):
        assert re.search(rf"^{score}:", rubric, re.MULTILINE)
    source = GUIDE.read_text(encoding="utf-8")
    for required in (
        "threshold <strong>4</strong>",
        "same dataset version, evaluator version, judge, threshold",
        "new agent output",
        "improve, tie or regress",
        "missing or failed rows",
        "Generated answers are suggestions",
        "frozen baseline set",
        "Sampling can return fewer rows",
        "would only rescore the past",
    ):
        assert required in source


def test_live_rehearsal_regressions_are_covered():
    rubric = snippet("style-rubric")
    candidate = snippet("candidate-instructions")
    assert "First check factual restraint" in rubric
    assert "assign 1 or 2 regardless of its friendly tone" in rubric
    assert "order number and photo ID" in rubric
    assert "Do not suggest unprovided verification methods" in candidate
    assert "You cannot perform an action even if the customer supplies its rules" in candidate
    source = GUIDE.read_text(encoding="utf-8")
    generation = source.split('id="card-generate"', 1)[1].split("</article>", 1)[0]
    assert "maximum samples to <strong>15</strong>" in generation
    assert "maximum samples to <strong>5</strong>" not in generation
    assert "mark generated-case review as unfinished" in generation
    assert "Do not switch tenants, change permissions or submit another job" in generation
    traces = source.split('id="card-traces"', 1)[1].split("</article>", 1)[0]
    core, optional = traces.split('<div class="reveal">', 1)
    assert "Copy the synthetic user query from that trace" in core
    assert "Agent / Individual turns" not in core
    assert "Agent / Individual turns" in optional
    assert "From traces" not in core
    assert "AppInsightsReadWithoutPrivateLink" in optional
    assert "only when your facilitator has confirmed" in optional


def test_review_batch_moves_recovery_and_applies_only_selected_deletions():
    source = GUIDE.read_text(encoding="utf-8")
    preflight = source.split('id="card-preflight"', 1)[1].split("</article>", 1)[0]
    baseline = source.split('id="card-baseline"', 1)[1].split("</article>", 1)[0]
    dataset = source.split('id="card-dataset"', 1)[1].split("</article>", 1)[0]
    candidate = source.split('id="card-candidate"', 1)[1].split("</article>", 1)[0]
    compare = source.split('id="card-compare"', 1)[1].split("</article>", 1)[0]
    assert "If a run fails" not in preflight
    assert "If the evaluation fails or stalls" in baseline
    assert "target <strong>Dataset</strong> would grade existing answers" not in baseline
    assert "Upload evaluation data" in dataset
    assert "Example user questions without answers." in dataset
    assert "Note the dataset version." in dataset
    assert "Without JavaScript, copy the text" not in dataset
    assert "; do not change it between the two runs" not in dataset
    assert "Check results and improve agent" in candidate
    assert "Open the baseline evaluation results" in candidate
    assert "IMPROVE YOUR AGENT</h2>" in source
    assert "Record baseline <strong>__/8</strong>" not in compare
    assert "Analyze Results" in compare
    assert "Skip it for this eight-case exercise" not in compare
    assert "Curate from traces" in dataset


def test_reference_download_preserves_original_cases_and_generator_has_separate_goal():
    source = GUIDE.read_text(encoding="utf-8")
    reference = re.search(r'id="reference-download".*?href="data:text/plain;base64,([^"]+)"', source)
    assert reference
    text = base64.b64decode(reference.group(1), validate=True).decode("utf-8")
    assert text.splitlines() == snippet("evaluation-dataset").splitlines()
    generation = source.split('id="card-generate"', 1)[1].split("</article>", 1)[0]
    assert 'download="pickup-style-reference.txt"' in generation
    assert "<strong>Reference file</strong> and a <strong>Prompt</strong>" in generation
    assert "it instructs the data generator, not your pickup agent" in generation
    assert "complaints and negative customer feedback" in snippet("generation-prompt")
    assert "do not grade the generator's suggested answer" in generation
    assert "built-in <strong>Relevance</strong>" in generation
    assert "The TXT file contains the same questions as the initial JSONL dataset." in generation
    assert "supported reference formats" not in generation
    assert "never call them tests, training cases, synthetic data or evaluation questions" in generation
    assert "Every query must say it is fictional" not in generation


def test_core_cards_keep_exact_text_steps_without_ui_captures():
    source = GUIDE.read_text(encoding="utf-8")
    candidate = source.split('id="card-candidate"', 1)[1].split("</article>", 1)[0]
    compare = source.split('id="card-compare"', 1)[1].split("</article>", 1)[0]
    assert "The saved version contains the same first three lines" not in candidate
    assert "No other agent configuration changed" not in candidate
    assert "<img" not in source
    assert "Screenshot" not in source
    assert "<strong>Add run</strong>" in compare
    assert "<strong>Configure agents</strong>" in compare
    assert "Read the statistical result as well as the score difference.</p>" in compare
    assert "; an improvement on eight questions is not strong evidence" not in compare
    assert 'id="card-keep"' not in source
    assert set(re.findall(r'<article\b[^>]*\bid="([^"]+)"', source)) == {
        "card-preflight", "card-dataset", "card-evaluator", "card-baseline",
        "card-candidate", "card-compare", "card-generate", "card-traces",
    }


def test_text_only_portal_setup_preserves_precise_click_targets():
    source = GUIDE.read_text(encoding="utf-8")
    for required in (
        "Build &rarr; Data &rarr; Datasets &rarr; Create dataset &rarr; Upload dataset",
        "<strong>Dataset purpose</strong>", "<strong>Dataset file</strong>",
        "categories <strong>Quality</strong> and <strong>Agents</strong>",
        "<strong>Evaluation prompt</strong>",
        "Build &rarr; Evaluations &rarr; Runs &rarr; Create",
        "Wait for its preview to load before continuing",
    ):
        assert required in source


def test_unrelated_topic_capture_and_optional_scope_evaluation_are_distinct():
    source = GUIDE.read_text(encoding="utf-8")
    traces = source.split('id="card-traces"', 1)[1].split("</article>", 1)[0]
    core, optional = traces.split('<div class="reveal">', 1)
    assert json.loads(snippet("offtopic-dataset")) == {"query": snippet("offtopic-query")}
    assert "quadratic equations" in snippet("offtopic-query")
    assert snippet("offtopic-query") not in snippet("evaluation-dataset")
    assert "pickup-unrelated-&lt;seat&gt;" in core
    assert "not the old response as ground truth" in core
    assert "do not explicitly require it to decline every unrelated request" in core
    assert "The core exercise is complete" in core
    assert "Rubric" not in core
    assert "If your editor offers" in optional
    assert "new quality target" in optional
    assert "threshold to <strong>0.8</strong>" in optional
    assert "one genuine pickup question" in optional
    assert "newly generated agent output" in optional
    assert "Leave the current agent instructions unchanged" in optional
    assert "blanket refusal" in snippet("scope-rubric-context")


def test_user_message_mapping_is_not_an_agent_instruction_override():
    source = GUIDE.read_text(encoding="utf-8")
    baseline = source.split('id="card-baseline"', 1)[1].split("</article>", 1)[0]
    compare = source.split('id="card-compare"', 1)[1].split("</article>", 1)[0]
    assert snippet("evaluation-user-prompt") == "{{item.query}}"
    assert "<strong>Version</strong> dropdown" in baseline
    for card in (baseline, compare):
        assert "<strong>Configure agents</strong>" in card
        assert "<strong>Add custom prompt</strong>" in card
        assert "<strong>USER</strong> message" in card
        assert "<strong>Save</strong>" in card and "<strong>Next</strong>" in card
    assert "not a replacement for the saved agent instructions" in baseline
    assert "Keep this mapping unchanged" in compare
    assert "agent instructions you saved in section 04" in compare
    assert "<strong>Version</strong> dropdown" in compare
    assert "select the saved candidate version" in compare
    assert "do not assume that <strong>Add run</strong> uses the latest version" in compare


def test_core_completion_extensions_and_safe_recovery_are_explicit():
    source = GUIDE.read_text(encoding="utf-8")
    assert "Core complete" in source
    assert "Optional: explore AI-based analysis" in source
    assert "Optional extensions: grow the test set" in source
    assert "do not change the core completion criteria" in source
    assert "Stop waiting after five minutes" in source
    assert 'id="resume-cleanup"' in source
    assert "<strong>Resume:</strong>" in source
    assert "<strong>Cleanup:</strong>" in source
    assert "facilitator owns" in source


def test_candidate_reuses_evaluation_and_exercises_compare_and_analysis():
    source = GUIDE.read_text(encoding="utf-8")
    compare = source.split('id="card-compare"', 1)[1].split("</article>", 1)[0]
    assert "existing <code>style-baseline-&lt;seat&gt;</code> evaluation" in compare
    assert "<strong>Add run</strong>" in compare
    assert "both completed runs" in compare
    assert "then select <strong>Compare runs</strong>" in compare
    assert "original run as <strong>Baseline</strong>" in compare
    assert "select both runs and select <strong>Analyze Results</strong>" in compare
    assert "Set up cluster analysis" in compare and "Start analysis" in compare
    assert "estimated consumption" in compare
    assert "Top 3 suggestions by AI" in compare and "AI categorized clusters" in compare
    assert "Context Summary" in compare and "<strong>Response</strong>" in compare
    assert "eight questions per run" in compare
    assert "larger, more varied datasets" in compare
    assert "Created on" in compare and "run IDs" in compare
    for obsolete in (
        "Evaluation &rarr; Create", "style-candidate-", "separate evaluation",
        "Why not just Add run", "Skip it for this eight-case exercise", "05a.png",
    ):
        assert obsolete not in compare


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch()
        yield instance
        instance.close()


@pytest.fixture(scope="module")
def standalone(tmp_path_factory):
    destination = tmp_path_factory.mktemp("lab3-standalone") / "lab3.html"
    subprocess.run(
        ["node", str(ROOT / "docs" / "assets" / "html-docs" / "bundle.js"), str(GUIDE), str(destination)],
        check=True, capture_output=True, text=True,
    )
    return destination


def open_dataset(browser, document=GUIDE, **options):
    context = browser.new_context(**options)
    context.route(re.compile(r"^https?://"), lambda route: route.abort())
    page = context.new_page()
    page.goto(document.as_uri())
    page.wait_for_function("Boolean(window.HtmlDocs)")
    page.locator("#card-dataset .card-toggle").click()
    page.get_by_role("button", name="Open the eight-row JSONL file", exact=True).click()
    return context, page


@pytest.mark.parametrize("document_kind", ["source", "standalone"])
def test_download_matches_the_importable_source(browser, tmp_path, standalone, document_kind):
    document = GUIDE if document_kind == "source" else standalone
    context, page = open_dataset(browser, document=document, accept_downloads=True)
    try:
        with page.expect_download() as pending:
            page.locator("#evaluation-dataset [data-lab-download]").click()
        download = pending.value
        assert download.suggested_filename == "pickup-style-v1.jsonl"
        destination = tmp_path / download.suggested_filename
        download.save_as(destination)
        expected = (INPUTS / destination.name).read_bytes()
        assert destination.read_bytes() == expected
        assert "Download requested" in page.locator("#evaluation-dataset [role=status]").inner_text()
        assert page.locator("a[download][href^='blob:']").count() == 0
    finally:
        context.close()


def test_failed_download_gives_actionable_copy_fallback(browser):
    context, page = open_dataset(browser)
    try:
        page.evaluate("() => { URL.createObjectURL = () => { throw new Error('Unavailable in this browser'); }; }")
        page.locator("#evaluation-dataset [data-lab-download]").click()
        status = page.locator("#evaluation-dataset [role=status]")
        assert "Download unavailable: Unavailable in this browser" in status.inner_text()
        assert "Use Copy" in status.inner_text()
        assert status.get_attribute("data-kind") == "error"
    finally:
        context.close()


def test_copy_exact_text_and_blocked_clipboard_fallback(browser):
    context, page = open_dataset(browser)
    try:
        page.evaluate("""Object.defineProperty(navigator, "clipboard", {
            configurable: true, value: {writeText: async text => {window.copied = text;}}
        })""")
        page.locator("#evaluation-dataset [data-lab-copy]").click()
        page.wait_for_function("typeof window.copied === 'string'")
        assert page.evaluate("window.copied") == snippet("evaluation-dataset")
        page.evaluate("""Object.defineProperty(navigator, "clipboard", {
            configurable: true, value: {writeText: async () => {throw new Error("Denied");}}
        })""")
        page.locator("#evaluation-dataset [data-lab-copy]").click()
        page.wait_for_function("document.querySelector('#evaluation-dataset [role=status]').dataset.kind === 'error'")
        assert page.evaluate("window.getSelection().toString()") == snippet("evaluation-dataset")
        assert "Ctrl+C" in page.locator("#evaluation-dataset [role=status]").inner_text()
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_mobile_reading_has_no_document_overflow(browser, theme):
    context, page = open_dataset(browser, viewport={"width": 390, "height": 844}, color_scheme=theme)
    try:
        page.locator("[data-action=expand-all]").click()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("#evaluation-dataset code").is_visible()
    finally:
        context.close()


def test_no_javascript_keeps_manual_dataset_and_every_instruction(browser):
    context = browser.new_context(java_script_enabled=False)
    try:
        page = context.new_page()
        page.goto(GUIDE.as_uri())
        for identifier in (
            "evaluation-dataset", "style-rubric", "candidate-instructions", "generation-prompt",
            "offtopic-query", "offtopic-dataset", "scope-rubric-context",
        ):
            assert page.locator(f"#{identifier} code").is_visible()
        for button in page.locator("[data-lab-download]").all():
            assert not button.is_visible()
        assert "pickup-style-v1.jsonl" in page.locator("#card-dataset").inner_text()
        assert page.locator("#reference-download").is_visible()
        assert page.locator("#card-traces .card-body").is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("document_kind", ["source", "standalone"])
def test_unrelated_dataset_download_matches_playground_message_offline(
    browser, tmp_path, standalone, document_kind
):
    document = GUIDE if document_kind == "source" else standalone
    context = browser.new_context(accept_downloads=True)
    context.route(re.compile(r"^https?://"), lambda route: route.abort())
    try:
        page = context.new_page()
        page.goto(document.as_uri())
        page.wait_for_function("Boolean(window.HtmlDocs)")
        page.locator("#card-traces .card-toggle").click()
        with page.expect_download() as pending:
            page.locator("#offtopic-dataset [data-lab-download]").click()
        download = pending.value
        assert download.suggested_filename == "pickup-unrelated.jsonl"
        destination = tmp_path / download.suggested_filename
        download.save_as(destination)
        assert json.loads(destination.read_text(encoding="utf-8")) == {
            "query": page.locator("#offtopic-query code").inner_text()
        }
        page.evaluate("""Object.defineProperty(navigator, "clipboard", {
            configurable: true, value: {writeText: async text => {window.copied = text;}}
        })""")
        page.locator("#offtopic-query [data-lab-copy]").click()
        page.wait_for_function("typeof window.copied === 'string'")
        assert page.evaluate("window.copied") == snippet("offtopic-query")
        page.get_by_role("button", name="Optional: create an AI-assisted scope evaluator and run it", exact=True).click()
        page.locator("#scope-rubric-context [data-lab-copy]").click()
        page.wait_for_function(
            "(expected) => window.copied === expected", arg=snippet("scope-rubric-context")
        )
    finally:
        context.close()


@pytest.mark.parametrize("document_kind", ["source", "standalone"])
def test_reference_file_download_works_offline(browser, tmp_path, standalone, document_kind):
    document = GUIDE if document_kind == "source" else standalone
    context = browser.new_context(accept_downloads=True)
    context.route(re.compile(r"^https?://"), lambda route: route.abort())
    try:
        page = context.new_page()
        page.goto(document.as_uri())
        page.wait_for_function("Boolean(window.HtmlDocs)")
        page.locator("#card-generate .card-toggle").click()
        with page.expect_download() as pending:
            page.locator("#reference-download").click()
        download = pending.value
        assert download.suggested_filename == "pickup-style-reference.txt"
        destination = tmp_path / download.suggested_filename
        download.save_as(destination)
        assert destination.read_text(encoding="utf-8").splitlines() == snippet("evaluation-dataset").splitlines()
    finally:
        context.close()


@pytest.mark.parametrize("document_kind", ["source", "standalone"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_only_setup_and_user_mapping_work_offline(browser, standalone, document_kind, theme):
    document = GUIDE if document_kind == "source" else standalone
    context = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme=theme)
    context.route(re.compile(r"^https?://"), lambda route: route.abort())
    try:
        page = context.new_page()
        page.goto(document.as_uri())
        page.wait_for_function("Boolean(window.HtmlDocs)")
        page.locator("[data-action=expand-all]").click()
        assert page.locator("img").count() == 0
        assert "Upload dataset" in page.locator("#card-dataset").inner_text()
        assert "Dataset purpose" in page.locator("#card-dataset").inner_text()
        assert "Evaluations" in page.locator("#card-baseline").inner_text()
        assert "Add run" in page.locator("#card-compare").inner_text()
        page.evaluate("""Object.defineProperty(navigator, "clipboard", {
            configurable: true, value: {writeText: async text => {window.copied = text;}}
        })""")
        page.locator("#evaluation-user-prompt [data-lab-copy]").click()
        page.wait_for_function("window.copied === '{{item.query}}'")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    finally:
        context.close()
