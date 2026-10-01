# Public baseline validation and delivery boundaries

The public site publishes Labs 1 through 5 as HTML reading guides only.
The one-day timetable is a design target; future labs and showcases remain
unpublished or separately qualified. Historical private evidence is not
distributed and does not certify this checkout or a new cloud environment.

## Lab 5, 2026-09-30

The [knowledge guide](../docs/guides/chapter-5-knowledge-base.html) and
[detailed qualification record](../student/labs/knowledge-base/VALIDATION.md)
separate a user-approved 20-case core from the full 100-case extension.
Isolated live runs completed both comparisons: both-metric success rose from
0/20 to 16/20 and from 0/100 to 79/100; all 480 core/full scores completed without
errors. Minimal extraction failed the raster-chart cases, as documented.
The core baseline took 3m 7s and its candidate 6m 29s; room timing remains
unqualified.

Actual portal checks covered Project Managed Identity connection, upload of all
20 PDFs after failed-file Retry recovery, KB creation, agent attachment, a
correct cited visible answer, dataset upload/preview, pinning and evaluator
configuration through Review, plus native comparison of the completed API jobs.
Native Submit/Add run clicks, attendee roles and concurrency, Blob ingestion and
multimodal extraction are not certified.

The final guide passed 291 canonical browser checks in all eight palettes,
offline and without JavaScript. Targeted content/navigation/export checks passed
except a pre-existing concurrent Lab 4 MIT-notice/export mismatch; that artifact
was not modified here. Independent educator, student/source, reproducibility
and destructive-safety review found two material verification gaps. The repaired
source/citation and case/score probes have negative tests, and a follow-up review
reported no blocking or material source/evidence finding. Live cleanup status is
recorded separately after its exact-scope verification.
The successful Lab 5 group is verified absent. The initial failed-creation group
has no listed resources but remains in Azure `Deleting`; the bounded cleanup
monitor reported nonzero and its exact state was retained for follow-up.

## Prepared prerequisites

Use Python 3.13+, the dependencies pinned in `uv.lock`, pytest, Playwright with
its matching Chromium and Node.js. The commands below do not install packages.
Node export tests also need an existing approved Playwright installation.
Canonical browser-validator subprocesses allow up to five minutes on slower
Windows hosts; a timeout remains a failed check rather than a skipped result.

When dependencies are missing, use your organization's approved package feed.
Inspect registry settings and package availability before installing. The
lockfile is retained; no SDK or dependency upgrade is part of this baseline.

## Local commands

From the repository root:

```powershell
python -m pytest
git diff --check
```

The browser collection verifies actual navigation, desktop/mobile light/dark
layouts, keyboard behavior, persisted preferences, copy/download controls,
local assets, no-JavaScript reading and isolated HTML exports. Content checks
verify that the published guide and downloadable synthetic inputs agree.

## Text-only lab boundary

UI screenshots and galleries are not published. Guides specify menu paths,
control labels, field values and expected results in text. Browser-test captures
may be generated under ignored `evidence`; they are not instructional assets.
The public-source checks reject reintroduction of the retired UI images.

## Preview

```powershell
python -m http.server 4173 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:4173/`; stop with Ctrl+C. Serve only `docs`, never the
repository root or private `.workshop` state. File and HTTP origins use separate
browser storage. Opening a guide does not prepare a cloud seat.

## Live qualification still required

Before delivery, qualify the exact attendee identity, models, controls, dataset
previews, trace access, region availability, quotas and concurrency. Rehearse
all three documented portal journeys and measure complete lab and day timing,
including recovery and breaks.

Local checks cannot certify cloud admission, policy enforcement, hosted routing,
native evaluation or the unpublished afternoon experience.

## Lab 1 and reading-only migration, 2026-09-30

HTML-docs 1.2.0 is vendored locally. All published labs and the lab-guide
template use Read only; no slide or sheet surface is loaded. The index and
teacher deck template also use the updated canonical heads. The concurrently
authored instrument catalog is excluded from this migration at the owner's
request.

Observed local evidence: Lab 1 passed the canonical 1280x720 validator's
256 checks, including eight palettes, legacy accent compatibility, print,
offline loading and no-JavaScript reading. Focused reading tests verified
copy, exact accent pairs, narrow/desktop layouts and print targeting.
All 15 focused workshop navigation, canonical-head and path-preserving offline
collection checks passed. Lab 2/3 inputs remain unchanged.
The changed-surface browser rerun passed all 34 rendering checks and all 29
workshop export/reading-control checks; catalog rendering was outside the
selected scope.
The final lab-content, reading-control and workshop-navigation rerun passed
all 74 checks. The new guide also exports as an offline standalone HTML file;
cross-lab navigation is validated in the path-preserving export collection.

Independent educator review identified a 20-minute versus Fireworks deployment
latency mismatch. The guide now separates the primary/Luna core and GLM
submission from deferred GLM success and hello checks. The follow-up
student/reproducibility/safety source review reported no material findings.
Live student and clean-room execution remain blocked: no assigned cloud seat or
authorization was provided. The reviewer did not claim a UI pass after its
file-origin stylesheet-inspection error; local browser evidence is separate.
An independent educator/UI review of all three guides, the index, actual
screenshots and narrow offline rendering identified an overly optimistic
20-minute summary on the index. It now matches the guide's core/deferred
boundary. No other material educator/UI findings were reported.
An independent follow-up on that repaired timing contract reported no
remaining material inconsistency.

A wider source run passed 332 checks but reported unrelated concurrent-work
failures: an `XXX` match in an instrument-catalog page and a local MCP `.env`
file. Neither file was edited or opened by this task. Those results do not
qualify the separate workstreams or the complete checkout.
