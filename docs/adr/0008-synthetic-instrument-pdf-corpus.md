# 0008. Synthetic instrument dossiers with durable offline HTML

- **Status:** Superseded by [0010](0010-shared-data-and-grounding-evals.md)
- **Date:** 2026-09-30
- **Deciders:** Workshop content maintainers

## Context

The knowledge chapter needs at least twenty substantial instrument documents
that exercise prose extraction, column order, numerical tables, charts, diagrams
and image interpretation. The request requires PDF files in Git and generated
instrument images from an authorized Foundry deployment using Entra login.
The repository requires synthetic identities, HTML attendee sources, offline
runtime assets and ignored visual-test evidence.

## Decision drivers

- Twenty distinct instrument families within one consistent fictional company.
- Five substantial text-only pages per dossier, not a short brochure stretched
  over empty pages.
- Meaningful raster-chart questions that cannot be answered from duplicate prose.
- Re-export PDFs without cloud credentials or the original image cache.
- Keep real cloud endpoints, tokens, customer identities and generation receipts
  out of distributable material.

## Options considered

### Option A - direct PDF-only authoring

Generate PDF with a document library. This can control geometry but leaves no
HTML attendee source and complicates accessible browser reading.

### Option B - linked HTML with versioned source images

Keep ordinary media files next to the HTML. This is easy to edit, but contradicts
the requested exclusion of raw generated imagery and requires a multi-file export.

### Option C - self-contained HTML and generated PDF

Embed compressed instrument imagery and raster charts in standalone HTML.
Keep raw images and private receipts ignored. Export offline using Chromium
and inspect the final PDF with PyMuPDF.

## Decision

Choose Option C. Store English HTML dossiers under `docs/instrument-catalog/`
and PDFs, editorial data, manifest and narrow authoring scripts under
`student/labs/knowledge-base/corpus/`. Store answer references separately under
`teacher/knowledge-corpus/`. Each dossier has nine A4 pages, with five prose-only
pages and four deliberately different visual/document layouts.

Use the existing canonical appearance bootstrap and token set, with blue-only
controls and a document-specific print layout. Do not modify shared UI assets.
Use the documented MAI image generations route and Cognitive Services Entra
token audience. Actual operator endpoint values remain command-line/local state,
never checked-in configuration.

## Consequences

PDF and HTML duplicates increase repository size, but both are requested
durable deliverables. Raw image generation is paid and can fail after a request
has been processed; retries require explicit approval and remain bounded.
Existing images are hash-checked and reused rather than regenerated silently.
No deployment, permission change or cloud deletion is part of corpus authoring.

The fictional company's common policies intentionally recur across dossiers;
instrument mechanisms, histories, artists, manufacturing stages, acceptance
criteria and numerical records distinguish the families. Generated imagery is
illustrative and cannot establish engineering dimensions or exact construction.

## Assumptions and revisit triggers

- English synthetic material is appropriate for the intended retrieval exercise.
  Revisit if a language or accessibility requirement changes.
- A prepared environment accepts these PDFs; no ingestion success is claimed.
  Revisit page or image budgets if the selected ingestion configuration imposes
  different documented limits.
- PDFs are explicitly required in Git. Revisit storage if repeated editions
  make binary history too large or that requirement changes.
- Image generation uses an existing approved deployment. Revisit the adapter
  if its documented API or Entra audience changes.

## Validation

The exporter checks offline asset loading, print geometry, two-column text
bounds, nine-page output, five substantial image-free pages and recognizable
numerical tables. It renders every PDF page into ignored evidence.
Corpus tests compare prose, table figures, visual presence, synthetic notices
and manifest hashes against the final PDFs. Independent review must inspect
the actual PDFs and rendered pages, not infer quality from generation success.

API reference checked on 2026-09-30:
[MAI image models](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-mai-image).
This decision does not certify a live knowledge-base deployment.
