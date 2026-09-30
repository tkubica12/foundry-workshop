# Instrument corpus validation

Edition: September 2026. Scope: synthetic documents, not cloud ingestion.
Paths reflect the role-neutral organization in ADR 0010.

- 20 final PDFs, nine pages each: 180 pages total.
- Five text-only pages per PDF; at least 464 extracted words on every such page.
- 40 instrument images generated with an existing MAI-Image-2.6 deployment and
  Entra authentication. Raw PNGs and generation receipts are ignored.
- Every PDF includes annotated external anatomy, a raster shipment chart,
  numerical model table, infographic and vector manufacturing/rework diagram.
- Manifest hashes match final PDF bytes. Grounding eval dataset contains 100
  page-referenced questions; do not ingest the answer key.

## Automated evidence

```powershell
uv sync --project data\instruments --locked
data\instruments\.venv\Scripts\python.exe -m pytest tests\test_instrument_corpus.py tests\test_docs_html.py tests\test_html_docs_exports.py
```

Before relocation: 357 checks passed in the isolated restored environment. Coverage
includes actual PDF pages and extracted content, offline assets, print fit,
recognizable tables, manifest integrity, canonical HTML heads, standalone
exports, links, mobile geometry, keyboard theme controls and redirect rejection.
Browser-reading checks refer to the previous, now removed HTML deliverables;
current corpus tests cover ignored print intermediates instead.

After relocation: 102 checks passed with the documented restored environment.
All 20 PDF hashes were preserved, and verification did not require Chromium,
Azure or the raw image cache. The generator uses ignored print intermediates;
the tests reconstruct visual fixtures from distributed PDFs rather than relying
on the author's image cache.
Dependency restoration used the approved Microsoft feed; shared root dependencies
and their lockfile were not changed by corpus authoring.

The final exporter verified every document and rendered every PDF page.
Visual captures remain under ignored `evidence/instrument-corpus/`.

## Independent review gates

Educator / PDF acceptance: opened all 20 actual PDFs, reviewed 180 pages,
visually opened every per-document contact sheet and every anatomy page at
full-page resolution, checked focused visual pages and all 100 answer references.
Final outcome: no blocking or material findings. Local evidence:
`evidence/instrument-corpus/educator-pdf-review.json`.

Safety / reproducibility: executed offline PDF re-export from an isolated
single-HTML starting state, repeat export, fit/inspection failure preservation
and repaired re-export. Identified and resolved authorization forwarding on
redirects and a missing isolated pytest dependency. Independent focused
re-review ran redirect/adapter regressions in the restored environment and
reported no remaining blocking or material findings. Local evidence:
`evidence/instrument-corpus/safety-reproducibility-review.json` and
`evidence/instrument-corpus/safety-reproducibility-rereview.json`.

Migration review: independently checked all moved PDF hashes and all 100
reference answers/pages, rebuilt and exported one dossier into ignored evidence,
verified missing-cache failure and browser-free verification, and ran 23 targeted
checks. Final outcome: no blocking or material findings. Local evidence:
`evidence/instrument-corpus/migration-review.json`.

The first reproducibility review observed a browser shutdown stall after
successful export/recovery stages; subsequent complete exports and final tests
finished normally. Clean dependency restoration was performed by the author and
verified by the re-review through imports, not independently downloaded twice.

## Limits

No knowledge source was deployed or ingested. Retrieval quality, image
verbalization in the selected ingestion configuration, citations, tenant access,
quotas and live lab timing still require separate cloud qualification.
Generated images are illustrative, not engineering drawings. All business
records, performers, factories and models are fictional.
