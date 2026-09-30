# Public baseline validation and delivery boundaries

The public site publishes Labs 2 and 3 and a browser-local learning passport.
The one-day timetable is a design target; future labs and showcases remain
unpublished or separately qualified. Historical private evidence is not
distributed and does not certify this checkout or a new cloud environment.

## Prepared prerequisites

Use Python 3.13+, the dependencies pinned in `uv.lock`, pytest, Playwright with
its matching Chromium, Node.js and PowerShell 7 on Windows. The commands below
do not install packages. Node export tests also need an existing approved
Playwright installation discoverable by the vendored validator.
Canonical browser-validator subprocesses allow up to five minutes on slower
Windows hosts; a timeout remains a failed check rather than a skipped result.

When dependencies are missing, use your organization's approved package feed.
Inspect registry settings and package availability before installing. The
lockfile is retained; no SDK or dependency upgrade is part of this baseline.

## Local commands

From the repository root:

```powershell
python .\teacher\demos\build-host-agent\scripts\verify_offline.py
python -m pytest tests\test_public_baseline.py tests\test_workshop_navigation.py tests\test_docs_html.py tests\test_docs_rendering.py tests\test_slides.py tests\test_chapter_2_content.py tests\test_chapter_3_content.py tests\test_learning_passport.py tests\test_workshop_fixtures.py tests\test_html_docs_exports.py -ra
git diff --check
```

The guarded verifier runs six trusted lifecycle/harness modules. It disables
ambient pytest configuration and dotenv loading, redirects state to temporary
paths and rejects network, subprocess and protected-state access. It is not a
security sandbox for arbitrary code. Browser/export checks run separately
because they require child processes and a temporary loopback server.

The browser collection verifies actual navigation, desktop/mobile light/dark
layouts, keyboard behavior, persisted preferences, copy/download controls,
local assets, no-JavaScript reading and isolated HTML exports. Fixture checks
verify integrity hashes and synthetic case contracts.

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

Before delivery, supply explicit nonsecret teacher and seat contracts, qualify
the exact attendee identity, models, controls, dataset previews, trace access,
region availability, quotas and concurrency. Rehearse the documented teacher
deploy/showcase/repeat-deploy/reset/cleanup path in isolated owned resources.
Measure complete lab and day timing, including recovery and breaks.

Renamed agent names and ownership markers intentionally do not adopt resources
from another workshop. Do not edit ownership metadata to make cleanup accept
them. Use their original authorized automation for their original resources.

Local checks cannot certify cloud admission, policy enforcement, hosted routing,
native evaluation, destructive cleanup or the unpublished afternoon experience.

## Public baseline evidence

On 2026-09-30, the exact staged source was exported to a clean directory and
validated without installing dependencies:

- guarded offline lifecycle and harness suite: 310 passed;
- public-boundary, navigation, HTML, responsive browser, accessibility,
  copy/download, lab-content, passport, fixture and isolated-export suite:
  239 passed;
- staged-source whitespace check: passed;
- customer/environment and secret-pattern scan: no matches;
- published UI captures: none.

Independent educator/student and teacher/reproducibility/safety reviews inspected
the actual artifacts and exercised the repaired journeys. Their final gate found
no blocking or material issue in the public baseline. Live cloud qualification
remains blocked until a new authorized teacher and attendee contract is supplied.
