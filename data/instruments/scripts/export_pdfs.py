"""Export and inspect the actual offline PDF corpus; never call a cloud service."""

import argparse
import hashlib
import json
from pathlib import Path
import re

import pymupdf
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[3]
CORPUS = Path(__file__).resolve().parents[1]
HTML = ROOT / ".workshop" / "instrument-corpus" / "html"
PDFS = CORPUS / "pdfs"
EVIDENCE = ROOT / "evidence" / "instrument-corpus"
TEXT_SECTIONS = ["history", "performers", "manufacturing", "quality", "ownership"]

FIT_CHECK = """() => {
  const failures = [];
  for (const page of document.querySelectorAll('.page')) {
    const boundary = page.getBoundingClientRect();
    const footer = page.querySelector('.footer').getBoundingClientRect();
    for (const child of page.children) {
      if (child.matches('.footer')) continue;
      const box = child.getBoundingClientRect();
      if (box.left < boundary.left - 1 || box.right > boundary.right + 1 ||
          box.bottom > footer.top - 5) failures.push(page.id + ': element overlaps page/footer');
    }
    for (const paragraph of page.querySelectorAll('.prose p')) {
      const range = document.createRange(); range.selectNodeContents(paragraph);
      const prose = paragraph.parentElement.getBoundingClientRect();
      for (const box of range.getClientRects()) {
        if (box.left < prose.left - 1 || box.right > prose.right + 1 ||
            box.bottom > prose.bottom + 1) failures.push(page.id + ': prose overflows two columns');
      }
    }
  }
  return [...new Set(failures)];
}"""


def inspect_pdf(path, item, render=True):
    with pymupdf.open(path) as document:
        if len(document) != 9:
            raise RuntimeError(f"{path.name}: expected 9 pages, found {len(document)}")
        counts = []
        for number, page in enumerate(document):
            text = page.get_text()
            words = len(re.findall(r"\b[\w'-]+\b", text))
            counts.append(words)
            if "Synthetic" not in text:
                raise RuntimeError(f"{path.name}: page {number + 1} lacks its synthetic-data notice")
            for block in page.get_text("blocks"):
                if block[6] == 0 and not page.rect.contains(pymupdf.Rect(block[:4])):
                    raise RuntimeError(f"{path.name}: extracted text leaves page {number + 1}")
            if number in range(1, 6):
                if words < 440 or page.get_images(full=True):
                    raise RuntimeError(f"{path.name}: text-only page {number + 1} fails volume/image requirements")
            if number in (0, 6, 7) and not page.get_images(full=True):
                raise RuntimeError(f"{path.name}: page {number + 1} is missing its visual")
            if render:
                directory = EVIDENCE / "renders" / item["slug"]
                directory.mkdir(parents=True, exist_ok=True)
                page.get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2)).save(str(directory / f"page-{number + 1:02d}.png"))
        for offset, section in enumerate(TEXT_SECTIONS, 1):
            source_text = document[offset].get_text()
            if section == "history" and str(item["first"]) not in source_text:
                raise RuntimeError(f"{path.name}: history does not contain first-model year")
            if section == "quality" and str(item["units"][-1]) not in source_text:
                raise RuntimeError(f"{path.name}: shipment count missing from quality page")
        if item["flagship"] not in document[7].get_text():
            raise RuntimeError(f"{path.name}: flagship table row is missing")
        return {"slug": item["slug"], "pages": len(document), "words_per_page": counts,
                "text_only_pages": 5, "instrument_images": 2, "raster_charts": 1,
                "tables": len(document[7].find_tables().tables),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def export_one(browser, item, output):
    source = HTML / f'{item["slug"]}.html'
    if not source.is_file():
        raise RuntimeError(f"Missing HTML source {source.name}; build it first.")
    context = browser.new_context(offline=True, java_script_enabled=False)
    page = context.new_page()
    errors, requests = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("requestfailed", lambda request: errors.append(f"Asset failed: {request.url[:120]}"))
    page.on("request", lambda request: requests.append(request.url))
    try:
        page.goto(source.as_uri())
        page.emulate_media(media="print")
        page.evaluate("document.fonts.ready")
        if not page.evaluate("Array.from(document.images).every(i=>i.complete && i.naturalWidth)"):
            raise RuntimeError(f"{source.name}: incomplete image")
        if any(url != source.as_uri() and not url.startswith("data:") for url in requests):
            raise RuntimeError(f"{source.name}: export requires an external asset")
        if errors:
            raise RuntimeError(f"{source.name}: {errors}")
        failures = page.evaluate(FIT_CHECK)
        if failures:
            raise RuntimeError(f"{source.name}: {'; '.join(failures)}")
        temporary = output.with_suffix(".pdf.partial")
        page.pdf(path=str(temporary), prefer_css_page_size=True, print_background=True,
                 tagged=True, outline=True)
        record = inspect_pdf(temporary, item)
        if record["tables"] < 1:
            raise RuntimeError(f"{source.name}: PDF numerical table is not recognizable")
        temporary.replace(output)
        return record
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", nargs="+")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    catalogue = json.loads((CORPUS / "catalog.json").read_text(encoding="utf-8"))
    items = [x for x in catalogue["instruments"] if not args.slug or x["slug"] in args.slug]
    if not items:
        parser.error("Unknown instrument slug")
    PDFS.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    records = []
    if args.verify_only:
        records = [inspect_pdf(PDFS / f'{item["slug"]}.pdf', item) for item in items]
    else:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                for item in items:
                    output = PDFS / f'{item["slug"]}.pdf'
                    records.append(export_one(browser, item, output))
            finally:
                browser.close()
    for record in records:
        print(f"Verified {record['slug']}.pdf: {record['pages']} pages, "
              f"{sum(record['words_per_page'])} words", flush=True)
    (EVIDENCE / "pdf-verification.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    if not args.slug:
        manifest = {
            "company": catalogue["company"], "edition": catalogue["edition"], "synthetic": True,
            "documents": records,
        }
        (CORPUS / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        questions = []
        for x in items:
            questions.extend([
                {"document": f'{x["slug"]}.pdf', "page": 2, "type": "prose",
                 "question": f"Where is the {x['name'].lower()} made and when was its first Aster Vale model introduced?",
                 "answer": f'{x["factory"]}, line {x["line"]}; {x["first"]}.'},
                {"document": f'{x["slug"]}.pdf', "page": 8, "type": "table",
                 "question": "How much more does Atelier cost than Foundation, and how many additional bench hours does it receive?",
                 "answer": f'EUR {x["prices"][1] - x["prices"][0]}; {x["hours"][1] - x["hours"][0]} hours.'},
                {"document": f'{x["slug"]}.pdf', "page": 8, "type": "image-only-chart",
                 "question": "Read the annual-shipment chart: how many units were dispatched in 2022?",
                 "answer": str(x["units"][2])},
                {"document": f'{x["slug"]}.pdf', "page": 7, "type": "annotated-image",
                 "question": "Which four external parts are labelled in the anatomy illustration?",
                 "answer": [part[0] for part in x["parts"]]},
                {"document": f'{x["slug"]}.pdf', "page": 9, "type": "diagram",
                 "question": "What is the failure branch of the acceptance decision?",
                 "answer": "Hold the instrument, rework the affected operation and repeat downstream checks before release."},
            ])
        target = ROOT / "evals" / "grounding" / "instruments.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"synthetic": True, "ingest": False, "questions": questions}, indent=2) + "\n",
                          encoding="utf-8")


if __name__ == "__main__":
    main()
