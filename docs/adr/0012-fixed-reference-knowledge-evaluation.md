# 0012. Fixed-reference knowledge comparison

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Workshop maintainer

## Context

Lab 5 compares a no-knowledge agent with a knowledge-connected agent using the
100 synthetic instrument questions. Most original questions repeat across PDFs
and are ambiguous without a dossier name. Without retrieval, there is no
retrieved context to use as a fair pre/post grounding reference. Groundedness
alone can reward abstention and does not establish correct answer coverage.
This extends [ADR 0010](0010-shared-data-and-grounding-evals.md), retaining its
canonical reference questions and existing PDF bytes.

## Decision drivers

- Test corpus-specific facts without leaking answers into the agent.
- Keep the reference and judge configuration identical across both runs.
- Distinguish answer support, coverage and actual retrieval.
- Make image-only failures visible rather than promising full PDF understanding.
- Provide one-click downloads from the docs-only preview server.

## Options considered

### Option A - runtime trace groundedness only

Useful for faithfulness to retrieved tool output, but the baseline has no
retrieval and therefore no equivalent context. A grounded refusal or a wrong
retrieved chunk can appear successful without answering the reference question.

### Option B - fixed curated reference plus completeness and a trace check

Use the existing answer as a short, explicitly curated judge-only context.
Measure corpus agreement with Groundedness, coverage with Response completeness,
and verify a real retrieved source independently. Short references require
manual inspection of judge disagreements and cannot certify whole-document
support.

## Decision

Choose Option B for the core comparison. Generate JSONL with stable case IDs,
PDF-qualified queries, string ground truth, curated context and evidence-type
metadata. Send only `query` to the agent. Preserve the canonical JSON unchanged.
Never ingest evaluation material. Keep instructions fixed before the baseline;
only connect knowledge for the candidate.

Observed full-run durations changed the delivery assumptions: the baseline took
16m 42s and the candidate 34m 46s before counting KB authoring and discussion.
The owner explicitly approved a 20-case core and a full 100-case extension.
Select one case per dossier, rotating the five evidence types in source order,
so each type has four core cases. Selection does not consult measured scores.
Use the same subset for both core versions; use all 100 for both full versions.
Keep the full references unchanged and never compare unequal test sets.

Use minimal text extraction for the core path. Multimodal enrichment and
trace-groundedness are separately defined extensions, not promises that raster
charts will work.

Generate a deterministic ZIP containing exactly the original 20 PDF files and
a matching JSONL asset under `docs/assets/knowledge-base/`. These download copies
are generated distributions, not additional authoring sources. This small
binary duplication permits a docs-only preview without exposing repository
state. The corpus manifest remains authoritative.

## Consequences

Two evaluators and source inspection are necessary. A high groundedness score
alone is not completion. Report each of the five evidence types separately.
Evaluation and indexing run asynchronously within a planned, not measured,
timebox. Require complete scored rows before drawing a before/after conclusion.

Use isolated tagged resource groups for operator qualification. Prefer
Serverless when actually admitted; keep explicit Basic/manual-connection
fallbacks. Never delete unrelated resources or weaken Storage network controls.

## Assumptions and revisit triggers

- Curated answers remain accurate for the manifest-pinned PDF edition. Regenerate
  and review references when the corpus changes.
- The portal exposes the required dataset fields and mappings. Revisit the core
  workflow if the UI cannot separate judge-only context from agent inputs.
- Minimal extraction intentionally cannot certify raster-chart understanding.
  Revisit the core choice if image interpretation becomes a required outcome.
- Generated copies remain practical for this 20-PDF corpus. Revisit distribution
  if corpus size makes repository/download duplication unreasonable.
- The balanced core fits the one-hour chapter with prepared models and a Search
  fallback. Revisit the room timebox if measured core jobs or uploads consume
  the recovery margin.

## Validation

Verify all manifest hashes, 100 rows, 20 rows per evidence type and exact archive
bytes. Browser-test the actual HTML and download path. Live qualification must
prove all 20 indexed filenames, an MCP tool call with correct evidence, and
completed before/after native evaluation rows. Keep private IDs and request logs
in ignored evidence, and record the observed scope in the lab validation record.
