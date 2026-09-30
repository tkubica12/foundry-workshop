# 0010. Shared PDF data and separate grounding evals

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Workshop owner

## Context

The owner requested role-neutral `data/` and `evals/` locations instead of
student inputs and teacher answers. They explicitly chose to remove both the
browser catalogue and committed HTML dossiers, retaining PDFs, editorial data,
the generator and evaluation references. This changes the distribution
assumptions of [ADR 0008](0008-synthetic-instrument-pdf-corpus.md).

## Decision drivers

- Shared ingestion data must not imply a teacher/student role.
- Reference answers must remain outside the ingested corpus.
- PDF is the only distributed instrument-document format.
- Existing reviewed PDF bytes must survive reorganization unchanged.
- Rebuild prerequisites must describe the loss of durable embedded HTML honestly.

## Options considered

### Option A - retain standalone HTML as private authoring source

Enables re-export without the raw image cache but adds a duplicate durable
document format. The owner declined this option.

### Option B - PDF data plus editorial generator and eval references

Keep PDF files, structured editorial records and prose/layout code.
Use ignored HTML solely as the browser's print intermediate.
Requires a local image cache or newly approved generation to rebuild.

## Decision

Choose Option B. Put the 20 PDFs under `data/instruments/pdfs/`, editorial data,
manifest and isolated authoring tools under `data/instruments/`, and 100 reference
questions under `evals/grounding/instruments.json`. Remove the published catalogue
and all committed instrument HTML. Preserve the existing PDF and eval bytes.

The synthetic corpus is an explicit data exception to attendee-guide HTML
publication, not a change to the format of lab instructions. Raw images and print
HTML remain ignored. Nothing deploys or ingests a knowledge base.

## Consequences

PDF verification and ingestion require no image cache or Azure. Rebuilding
requires the 40 raw images; a fresh clone lacks them and needs separately
approved generation. The generator must fail clearly when those assets are absent.
No additional generation is authorized merely by reorganizing the repository.

The questions are a baseline grounding eval dataset, not an execution harness,
holdout or measured benchmark. Grade correctness and cited-evidence support
separately and report by evidence type. Never ingest reference answers.

## Assumptions and revisit triggers

- PDF remains the requested ingestion format. Revisit if the owner needs another
  durable document format.
- The local source-image cache suffices for current authoring. Revisit storage
  if clean-machine rebuild without paid generation becomes mandatory.
- The simple reference schema suffices for manual or future automated evaluation.
  Revisit when a specific runner, grader, threshold or holdout is selected.

## Validation

Compare all 20 moved PDFs against their existing manifest hashes and retain the
100 references unchanged. Verify every PDF and reference page at the new paths.
Build print intermediates only under the ignored local directory and exercise
offline rendering without changing the distributed PDFs. Check workshop
navigation after removing the catalogue and independently review the relocated
authoring/recovery instructions.
