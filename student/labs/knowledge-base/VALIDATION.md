# Knowledge lab qualification boundary

## Student-identity keyless rehearsal, 2026-10-01

A newly created, unrelated Entra account signed into a task-only Edge profile.
Its verified profile matched the test identity. Access was limited to the
isolated rehearsal group: Owner, Foundry User and Search Index Data Contributor
(plus Storage Blob Data Contributor, unused by this path). It had no Owner
access to shared groups. This proves the personal-group role contract, not a
reduced least-privilege configuration.

Basic Search in West Europe and Foundry in Sweden Central had local
authentication disabled. Search's system identity held Cognitive Services User
on Foundry; the project identity held Search Index Data Reader on Search.
The student connected Search with Project Managed Identity, created a native
file source and a Low/extractive KB, and used the prepared
`text-embedding-3-small` / `1` and `gpt-5-mini` / `2025-08-07` deployments.
The portal explicitly reported managed-identity model authentication.
Source and vectorizer definitions had null API keys and null authIdentity.

Bulk upload returned eight HTTP 429 responses, not 403. Completion was 12/20;
failed-file-only Retry reached 19/20 and a second Retry reached 20/20. The proxy
did not supply Retry-After or x-ms-request-id in the observed retry response.
All 20 distinct PDF names appeared in 300 indexed chunks; a stored embedding
had 1,536 nonzero dimensions and live text vectorization returned the acoustic
guitar evidence. No Storage account or keys were used.

The student's actual Playground response completed a
`knowledge_base_retrieve` MCP call, returned Alder Works, S1 and 1962, and cited
matching acoustic-guitar snippets supporting all three facts. The raw response,
not a second privileged inference, was retrieved and checked. The portal's
new-agent default included Web search; it was removed before the query.

The same student also exercised Add sources / Use existing sources / Add
existing, created a second KB from the already processed 20-file source, and
attached it to the existing agent. A new version containing only that KB
returned the same cited facts. This is the guide's prepared-source core path;
it removes bulk-upload throttling and resource provisioning from the timebox.
The existing comparison/evaluation settings remain unchanged; this rehearsal
did not resubmit the previously qualified 20-row evaluation pair.

A separate operator REST probe used standard extraction with no aiServices,
embedding or chat model API keys. West Europe Search called Sweden Central
Foundry/Content Understanding with its system identity. Actual extracted
content represented the raster chart as `2022 -> 502`; an MCP-backed agent
answered 502 with a citation to that image-derived chunk. Only
acoustic-guitar.pdf was probed. This does not qualify the complete multimodal
corpus, the portal's Advanced settings, Spain Central or concurrent seats.

Current first-party region tables list agentic retrieval and AI enrichment in
Sweden Central and West Europe, but not Spain Central. Content Understanding
lists Sweden Central and West Europe, not Spain Central. Earlier Search
capacity rejection and the new embedding quota rejection were not bypassed:
deployment resumed only after authorized unrelated cleanup released quota.
The models retained GlobalStandard; no automatic SKU/region change occurred.

Private evidence remains under ignored `.workshop/knowledge-base/`: native
profile/portal observations, source definition, index/vector checks, the
original student response, prepared-source selection/answer and standard
chart chunks/response. Room concurrency, complete 45-minute delivery pacing,
least-privilege access and Blob ingestion remain unqualified.

Independent review inspected the actual changed guide and private evidence.
The Student tester newly created a review KB from the existing 20-file source
with the documented Low/extractive settings, and passed offline keyboard,
disclosure, copy/download and theme checks. Attachment and answer checks used
the recorded student journey; the reviewer did not claim a fresh complete
evaluation pair or room rehearsal. The access/destructive-safety reviewer found
no material issue. Educator review identified an unexecutable attendee inventory
check: complete distinct-filename certification now belongs to operator
`prepare`/`verify` preflight, separately from attendee relevance checking.
The follow-up found no new material learning issue; its explicit operator-gate
and review-record requests are included here and in the operator README.

Thirty targeted content/model-continuity tests passed, and the canonical guide
validator passed 308 checks in all eight palettes, offline, reduced-motion,
print and no-JavaScript modes. A broader model-continuity run also encountered
pre-existing Chapter 6/7 expectations; those unrelated guides were not changed.

Final Educator verification confirmed the explicit inventory preflight and
review-evidence repairs with no blocking/material issue. The new rehearsal
resource group was deleted and its absence verified. The new test user and
group were permanently deleted; the local TAP export and task browser profile
were removed. Foundry soft-delete retention was not purged. No original
workshop resources or identities were changed by this rehearsal.

## Concise reading guide, 2026-10-01

The guide was shortened from 3,616 to 1,820 body words (about 50%). Core paths,
downloads, pinned versions, judge-only references, 20/40 result checks, retrieval
evidence, failed-file-only Retry, capacity fallback and shared-resource cleanup
boundaries remain. Existing live evaluation and ingestion evidence below is
unchanged; no duplicate cloud job was submitted to validate editorial changes.
The combined source/browser/navigation suite passed 138 tests and the canonical
validator passed 308 checks in all eight palettes, offline and without JavaScript.
Independent Educator/local Student and safety reviews reported no material issues.

The guide uses fixed judge-only curated answer references for corpus agreement
and Response completeness for answer coverage. Actual retrieved content and
citations are checked independently. Reference answers are never ingested or
placed in agent input messages. Text-only extraction is not a claim of image
understanding.

Local validation covers 100 unique document-qualified questions, 20 cases per
evidence type, all PDF hashes, deterministic download assets, HTML reading
controls, offline rendering and no-JavaScript content.

Live evidence is retained under ignored `.workshop/knowledge-base/`. The
rehearsal has exercised resource creation, managed-identity permissions, direct
uploads of all 20 PDFs and the actual MCP-backed agent answer. Serverless and
Basic creation in Sweden Central were rejected for regional capacity; Basic in
West Europe was admitted. An advertised regional feature is not live capacity.
`gpt-4o-mini` appeared in the model list but new deployment was rejected as
deprecating; the admitted rehearsal model is `gpt-5-mini`.

Transport failures occurred with Python HTTP upload requests. Windows curl
completed the identical direct uploads; bearer tokens are passed only in stdin,
not command-line arguments or files. A Blob fallback attempt encountered
environment-disabled Storage public networking. That control was not weakened;
Blob ingestion is not qualified by this attempt.

## Observed native portal path, 2026-09-30

Under the isolated operator-owned project, the actual Foundry portal completed
Project Managed Identity connection, direct upload of 20 PDFs, creation of a
second source and KB, `Use in an agent`, and the exact manual query in Playground.
The upload succeeded after two failed-file-only Retry rounds (12/20, then 19/20,
then 20/20); resubmitting all files was not necessary. The visible answer gave
Alder Works, line S1 and 1962 with two source references. Private UI evidence is
under `evidence/knowledge-base/`, never published.

Native dataset upload succeeded. The evaluation wizard previewed all seven
columns in its Top 5 rows, exposed `Pin v1`, the USER-only query template, the
two built-in evaluators, threshold 3 and the documented mappings through its
final Review screen. Removing all auto-suggested criteria avoids 23 unrelated
evaluators. No duplicate 100-row UI job was submitted merely to repeat the
completed API jobs. The native Submit and Add run clicks are not independently
certified by the Review-screen inspection.

The actual completed 100-row runs were also opened in native **Compare runs**.
It displayed the same mean scores as the raw rows: 2.05 versus 4.36 and 1.05
versus 4.06. This is observed result navigation, not a substitute for testing
native job-submission clicks.

## Completed live evaluation

Both native cloud evaluation jobs were submitted via the project API and
completed with 100 unique answers and 200 completed numeric evaluator scores
each. Neither run has errored or skipped rows. Agent and judge:
`gpt-5-mini` / `2025-08-07`; unchanged instructions; minimal extraction;
`text-embedding-3-small` / `1`; fixed curated references; threshold 3.
The results are one observed development run, not a repeatability guarantee.

| Evidence | Baseline groundedness | Candidate groundedness | Baseline completeness | Candidate completeness |
| --- | --- | --- | --- | --- |
| Prose | 3/20 | 20/20 | 0/20 | 20/20 |
| Table | 1/20 | 20/20 | 0/20 | 20/20 |
| Image-only chart | 1/20 | 0/20 | 0/20 | 0/20 |
| Annotated image | 0/20 | 19/20 | 1/20 | 19/20 |
| Diagram | 0/20 | 20/20 | 0/20 | 20/20 |
| Total | 5/100 | 79/100 | 1/100 | 79/100 |

Mean scores rose from 2.05 to 4.36 for Groundedness and from 1.05 to 4.06 for
Response completeness. Passing both metrics rose from 0/100 to 79/100.
All 20 raster chart questions failed; one annotated-image question also failed.
These outcomes support the core text-path comparison, not universal PDF/image
understanding. The baseline contains judge disagreements; read its reasons
rather than equating abstention with a guaranteed groundedness failure.

Strict probes check all 20 distinct filenames among 300 indexed chunks and
require the named MCP tool, matching acoustic-guitar evidence, all three manual
facts and actual matching citation URLs. Repeating preparation preserved the
saved versions and existing file count. An independent review found two
success-shaped probe gaps; explicit case/score and source/citation validators
with negative tests now address them.

Attendee least-privilege access, concurrent-seat capacity and the complete
45-minute hands-on/15-minute recovery target remain separately unqualified.
Full 100-row jobs ran for tens of minutes; start the baseline early and retain
the documented resume path rather than promising both jobs finish in the slot.
The Blob and multimodal extensions are not live-qualified.

## Owner-approved balanced core

After observing the full-run duration, the owner explicitly approved 20 balanced
core questions and the full 100 as an extension. The subset rotates evidence
types across all 20 dossiers, without consulting scores. Both 20-row live jobs
completed with 40 scores each and zero errors/skips. Groundedness improved from
1/20 to 16/20; completeness from 0/20 to 16/20. Passing both improved from 0/20
to 16/20. All four chart cases failed; all four cases in each other category
passed in the candidate. The complete room timebox remains a delivery rehearsal,
not a consequence of reducing the row count.
The observed core durations were 3m 7s and 6m 29s, respectively.

The independent follow-up inspected the actual raw rows and UI evidence, passed
all 19 targeted tests and found no remaining blocking/material source or
evidence issue. It did not assert a fresh attendee-identity cloud pass.

## Cleanup outcome

The successful rehearsal group was deleted and its absence verified; raw rows,
PDF hashes and local UI evidence remain available. The separate initial group
from rejected regional creation attempts has an empty ARM resource ledger but
remained in `Deleting` after the bounded monitor expired. Cleanup returned
nonzero and retained its exact scope in ignored state for follow-up; group
deletion is not falsely reported as complete. No soft-deleted Foundry account
was purged. The task-only browser was stopped and its separate profile removed.
