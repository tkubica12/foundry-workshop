# Synthetic instrument corpus

Ingest only the 20 files in [`pdfs/`](pdfs/) into the prepared knowledge source.
The PDFs are shared input data, not a teacher demo or an attendee guide.
The company, models, factories, performers and business records are fictional.

Each PDF has nine A4 pages: five substantial text-only pages, two generated
instrument illustrations, annotated parts, a raster chart, an infographic,
a numerical model table and a manufacturing/rework diagram.

[`catalog.json`](catalog.json) and `scripts/build_corpus.py` hold the editorial
data and authored prose/layout. [`manifest.json`](manifest.json) records final
PDF hashes and page metrics. The [grounding eval dataset](../../evals/grounding/)
is separate and must not be ingested.

## Verify existing PDFs

From the repository root:

```powershell
uv sync --project data\instruments --locked
data\instruments\.venv\Scripts\python.exe data\instruments\scripts\export_pdfs.py --verify-only
data\instruments\.venv\Scripts\python.exe -m pytest tests\test_instrument_corpus.py
```

Verification needs neither Azure nor raw images. The lockfile uses the approved
Microsoft feed and pins Python 3.13-compatible authoring tools.
No script commits or pushes files.

## Rebuild PDFs

PDF authoring is supported on Windows. The local source-image cache contains
40 PNGs and hash receipts under ignored `.workshop/instrument-corpus/images/`.
It is not included in a fresh clone. Regeneration on a clean machine needs
newly approved paid image generation; the existing PDFs can be used and verified
without it.

With the complete image cache and an approved installed Chromium:

```powershell
data\instruments\.venv\Scripts\python.exe data\instruments\scripts\build_corpus.py
data\instruments\.venv\Scripts\python.exe data\instruments\scripts\export_pdfs.py
```

Always rebuild after changing editorial data or prose. HTML exists only as a
local print intermediate in ignored `.workshop/instrument-corpus/html/`.
There is no published browser catalogue and no committed HTML dossier.
Full export refreshes the manifest and the eval references. `--slug acoustic-guitar`
narrows a build/export; run full verification afterward to refresh all references.

If Chromium is missing, install it only when browser downloads are permitted:

```powershell
data\instruments\.venv\Scripts\python.exe -m playwright install chromium
```

On a missing-image error, prepare the cache first. On a fit error, shorten or
restructure prose rather than clipping it. Failed export preserves the previous
PDF; fix the source, rebuild and repeat export. Visual evidence belongs in
ignored `evidence/instrument-corpus/`.

## Generate images deliberately

Use an existing authorized MAI image deployment. This is optional paid
authoring work, never a prerequisite for ingesting the distributed PDFs.

```powershell
az login
$env:FOUNDRY_RESOURCE_ENDPOINT = 'https://<resource-name>.services.ai.azure.com'
$env:FOUNDRY_IMAGE_DEPLOYMENT = '<approved-MAI-image-deployment>'
data\instruments\.venv\Scripts\python.exe data\instruments\scripts\generate_images.py --endpoint $env:FOUNDRY_RESOURCE_ENDPOINT --deployment $env:FOUNDRY_IMAGE_DEPLOYMENT --limit 40
```

Authentication uses the Azure CLI's Entra session. Tokens and actual endpoint
values are never written into distributable files; redirects are rejected.
The scripts create no cloud resources, change no permissions and delete nothing.
Existing image pairs are verified against prompt, deployment and image hashes.
Cache mismatches or incomplete pairs stop for inspection.

There are no retries by default. After explicitly approving possible duplicate
charges, `--retries 5` permits five additional attempts per image with bounded
backoff. Authentication, configuration and non-transient errors stop.
A network failure after submission can leave the billing outcome unknown.
Use `--slug acoustic-guitar --view hero` to scope an image operation.

[Validation and independent-review evidence](VALIDATION.md).
