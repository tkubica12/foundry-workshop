# Instrument grounding eval dataset

[`instruments.json`](instruments.json) contains 100 reference questions:
five evidence types for each of the 20 [instrument PDFs](../../data/instruments/pdfs/).
This is an eval dataset, not an eval runner or a measured quality result.

Each case contains:

- `document`: filename relative to `data/instruments/pdfs/`.
- `page`: one-based PDF page containing the reference evidence.
- `type`: `prose`, `table`, `image-only-chart`, `annotated-image` or `diagram`.
- `question`: the prompt to test.
- `answer`: the expected reference answer, as text or a list.

The top-level `ingest: false` is a data-handling convention, not an enforced
access control. Upload only the PDFs, never this dataset, `catalog.json` or the
manifest. Otherwise answers can leak into retrieval and invalidate the exercise.
Check the corpus manifest hashes before comparing runs.

## Assess grounding

Run a question against the knowledge-backed agent without providing the
reference answer. Preserve its answer, retrieved evidence and page citations.
Judge answer correctness separately from whether its claims are supported by
the cited PDF evidence. Compare equivalent meanings rather than demanding an
exact string match; list order is not significant for the anatomy labels.

Report results by evidence type, not just an overall average. Table cases need
correct arithmetic and units; chart cases intentionally require reading the
raster chart; anatomy and process cases need image or diagram interpretation.
The page references are checks for evidence, not guarantees of the citation
format produced by a particular retrieval system.

The set is a baseline regression exercise with repeated question patterns,
not an independent holdout or a complete grounding benchmark. It has no
unanswerable, adversarial or multi-document cases, no prescribed grader and
no acceptance threshold. No live Foundry IQ run or image-verbalization success
is claimed.

Regenerate references only when deliberately updating the corpus. Full
`data/instruments/scripts/export_pdfs.py` export or `--verify-only` refreshes
this dataset from the matching editorial records after checking the PDFs.
