"""Check the delivered PDF data, not merely the authoring inputs."""

import importlib.util
import json
from pathlib import Path
import re

import pymupdf
import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "instruments"
EVALS = ROOT / "evals" / "grounding" / "instruments.json"
DATA = json.loads((CORPUS / "catalog.json").read_text(encoding="utf-8"))
ITEMS = DATA["instruments"]
SECTIONS = ["history", "performers", "manufacturing", "quality", "ownership"]


def module(name):
    spec = importlib.util.spec_from_file_location(name, CORPUS / "scripts" / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_twenty_distinct_dossiers_and_consistent_model_records():
    assert len(ITEMS) == 20
    assert len({x["slug"] for x in ITEMS}) == 20
    assert len({x["code"] for x in ITEMS}) == 20
    assert len(list((CORPUS / "pdfs").glob("*.pdf"))) == 20
    assert not list(CORPUS.glob("*.html"))
    assert not list((ROOT / "docs" / "instrument-catalog").glob("*.html"))
    for x in ITEMS:
        assert 1958 <= x["first"] < x["launch"] <= 2026
        assert all(a < b for a, b in zip(x["prices"], x["prices"][1:]))
        assert len(x["stages"]) == len(x["stage_details"]) == 6
        assert len(x["parts"]) == 4
        assert len(x["units"]) == len(x["returns"]) == 6


@pytest.mark.parametrize("item", ITEMS, ids=lambda x: x["slug"])
def test_actual_pdf_meets_every_document_requirement(item):
    record = module("export_pdfs").inspect_pdf(CORPUS / "pdfs" / f'{item["slug"]}.pdf',
                                                 item, render=False)
    assert record["pages"] == 9
    assert record["tables"] >= 1
    assert min(record["words_per_page"][1:6]) >= 440
    with pymupdf.open(CORPUS / "pdfs" / f'{item["slug"]}.pdf') as pdf:
        text = "\n".join(page.get_text() for page in pdf)
        for value in [item["factory"], item["flagship"], item["artist"], item["second_artist"]]:
            assert value in text
        table_text = pdf[7].get_text()
        for value in item["prices"]:
            assert f"{value:,}" in table_text
        assert "Hold / rework / recheck" in pdf[8].get_text()
        assert pdf[8].get_drawings(), "manufacturing route must contain vector geometry"
        for part, _, _ in item["parts"]:
            assert part in pdf[6].get_text()
        assert len({image[0] for page in pdf for image in page.get_images(full=True)}) == 3
        assert "Synthetic training corpus" in pdf[0].get_text()


def test_manifest_and_eval_references_match_final_pdfs():
    import hashlib

    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert len(manifest["documents"]) == 20
    for row in manifest["documents"]:
        binary = (CORPUS / "pdfs" / f'{row["slug"]}.pdf').read_bytes()
        assert hashlib.sha256(binary).hexdigest() == row["sha256"]
    answers = json.loads(EVALS.read_text(encoding="utf-8"))
    assert answers["ingest"] is False
    assert len(answers["questions"]) == 100
    for question in answers["questions"]:
        assert (CORPUS / "pdfs" / question["document"]).is_file()
        assert 1 <= question["page"] <= 9
    for x in ITEMS:
        query = next(q for q in answers["questions"] if q["document"] == f'{x["slug"]}.pdf'
                     and q["type"] == "image-only-chart")
        assert query["answer"] == str(x["units"][2])
        with pymupdf.open(CORPUS / "pdfs" / f'{x["slug"]}.pdf') as pdf:
            assert not re.search(rf"\b2022\b[^.]*\b{x['units'][2]}\s+units\b",
                                 "\n".join(p.get_text() for p in pdf)), (
                "2022 shipment values must require chart interpretation, not duplicate prose"
            )


def test_ignored_print_intermediates_fit_without_external_assets(tmp_path):
    builder = module("build_corpus")
    exporter = module("export_pdfs")
    assert builder.HTML == exporter.HTML == ROOT / ".workshop" / "instrument-corpus" / "html"
    builder.CACHE = tmp_path / "images"
    builder.CACHE.mkdir()
    for item in ITEMS:
        with pymupdf.open(CORPUS / "pdfs" / f'{item["slug"]}.pdf') as pdf:
            for number, view in [(0, "hero"), (6, "anatomy")]:
                xref = pdf[number].get_images(full=True)[0][0]
                pymupdf.Pixmap(pdf, xref).save(str(builder.CACHE / f'{item["slug"]}-{view}.png'))
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        try:
            context = browser.new_context(offline=True, java_script_enabled=False)
            page = context.new_page()
            for x in ITEMS:
                source = tmp_path / f'{x["slug"]}.html'
                source.write_text(builder.dossier(x, DATA["notice"]), encoding="utf-8")
                page.goto(source.as_uri())
                page.emulate_media(media="print")
                assert page.locator(".page").count() == 9
                assert page.locator(".prose").count() == 5
                assert page.evaluate("Array.from(document.images).every(i=>i.complete&&i.naturalWidth)")
                assert page.evaluate(exporter.FIT_CHECK) == []
                for section in SECTIONS:
                    assert len(page.locator(f"#{section} .prose").inner_text().split()) >= 420
            context.close()
        finally:
            browser.close()


def test_missing_source_images_fail_without_cloud_generation(tmp_path):
    builder = module("build_corpus")
    builder.CACHE = tmp_path
    with pytest.raises(RuntimeError, match="Missing generated image"):
        builder.dossier(ITEMS[0], DATA["notice"])


def test_generation_adapter_has_no_paid_default_retry_or_secret_configuration():
    generator = module("generate_images")
    for x in ITEMS:
        for view in ["hero", "anatomy"]:
            prompt = generator.prompt_for(x, view)
            assert x["image"] in prompt
            assert "No people" in prompt
    tracked_sources = list((CORPUS / "scripts").glob("*.py")) + [CORPUS / "catalog.json"]
    forbidden = re.compile(r"https://[^<\s\"']+\.services\.ai\.azure\.com|Bearer\s+eyJ|api-key", re.I)
    for source in tracked_sources:
        assert not forbidden.search(source.read_text(encoding="utf-8")), source


def test_image_adapter_rejects_redirects_without_forwarding_authorization():
    from urllib.request import Request

    generator = module("generate_images")
    request = Request("https://fictional.services.ai.azure.com/mai/v1/images/generations",
                      data=b"{}", headers={"Authorization": "Bearer synthetic-test-sentinel"})
    for status in [301, 302, 303, 307, 308]:
        with pytest.raises(RuntimeError, match="without forwarding authorization"):
            generator.NoRedirects().redirect_request(
                request, None, status, "redirect", {}, "https://example.invalid/other"
            )
