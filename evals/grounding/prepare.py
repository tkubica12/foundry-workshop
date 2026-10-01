"""Build judge-only reference rows without changing the canonical questions."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def rows():
    source = json.loads((HERE / "instruments.json").read_text(encoding="utf-8"))
    if source.get("synthetic") is not True or source.get("ingest") is not False:
        raise ValueError("Reference data must be synthetic and excluded from ingestion")
    questions = source["questions"]
    if len(questions) != 100:
        raise ValueError("Expected exactly 100 reference questions")
    manifest = json.loads((ROOT / "data/instruments/manifest.json").read_text(encoding="utf-8"))
    hashes = {f'{item["slug"]}.pdf': item["sha256"] for item in manifest["documents"]}
    result = []
    for i, q in enumerate(questions, 1):
        document = q["document"]
        if document not in hashes or Path(document).name != document:
            raise ValueError(f"Unknown PDF: {document}")
        pdf = ROOT / "data/instruments/pdfs" / document
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != hashes[document]:
            raise ValueError(f"PDF hash mismatch: {document}")
        answer = q["answer"]
        if isinstance(answer, list):
            answer = "; ".join(answer)
        if not isinstance(answer, str) or not answer.strip() or not 1 <= q["page"] <= 9:
            raise ValueError(f"Invalid reference: {document}")
        result.append({
            "case_id": f"instrument-{i:03d}",
            "query": f'In the fictional Aster Vale dossier "{document}": {q["question"]}',
            "ground_truth": answer,
            "context": (
                f'Curated reference for "{document}", PDF page {q["page"]}. '
                f'Question: {q["question"]}\nReference answer: {answer}'
            ),
            "document": document,
            "page": q["page"],
            "evidence_type": q["type"],
        })
    return result


def core_rows(all_rows):
    kinds = ("prose", "table", "image-only-chart", "annotated-image", "diagram")
    documents = list(dict.fromkeys(row["document"] for row in all_rows))
    if len(documents) != 20:
        raise ValueError("Core selection requires exactly 20 dossiers")
    selected = []
    for i, document in enumerate(documents):
        matching = [row for row in all_rows if row["document"] == document and row["evidence_type"] == kinds[i % 5]]
        if len(matching) != 1:
            raise ValueError(f"Missing or ambiguous core case for {document}")
        selected.append(matching[0])
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--bundle", action="store_true", help="Build the attendee download assets")
    args = parser.parse_args()
    all_rows = rows()
    projections = {
        "instruments-evaluation.jsonl": all_rows,
        "instruments-evaluation-core.jsonl": core_rows(all_rows),
    }
    for name, projection in projections.items():
        expected = "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in projection)
        output = HERE / name
        if args.check:
            if not output.is_file() or output.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"{name} is missing or stale; run prepare.py")
        else:
            output.write_text(expected, encoding="utf-8", newline="\n")
        if args.bundle:
            destination = ROOT / "docs/assets/knowledge-base"
            destination.mkdir(parents=True, exist_ok=True)
            dataset = destination / output.name
            if args.check:
                if dataset.read_text(encoding="utf-8") != expected:
                    raise SystemExit(f"Attendee asset {name} is stale")
            else:
                dataset.write_text(expected, encoding="utf-8", newline="\n")
    if args.bundle:
        if args.check:
            with zipfile.ZipFile(destination / "instruments-pdfs.zip") as archive:
                names = sorted(p.name for p in (ROOT / "data/instruments/pdfs").glob("*.pdf"))
                if sorted(archive.namelist()) != names:
                    raise SystemExit("Attendee PDF archive file list differs")
                for name in names:
                    if archive.read(name) != (ROOT / "data/instruments/pdfs" / name).read_bytes():
                        raise SystemExit(f"Attendee archive differs: {name}")
        else:
            with zipfile.ZipFile(destination / "instruments-pdfs.zip", "w") as archive:
                for pdf in sorted((ROOT / "data/instruments/pdfs").glob("*.pdf")):
                    info = zipfile.ZipInfo(pdf.name, (2026, 9, 30, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info, pdf.read_bytes())
    print("100 full / 20 balanced core questions; judge-only context; all 20 PDF hashes verified")


if __name__ == "__main__":
    main()
