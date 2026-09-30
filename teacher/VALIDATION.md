# Public baseline validation and delivery boundaries

The public site publishes Labs 2 and 3.
The one-day timetable is a design target; future labs and showcases remain
unpublished or separately qualified. Historical private evidence is not
distributed and does not certify this checkout or a new cloud environment.

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
both documented portal journeys and measure complete lab and day timing,
including recovery and breaks.

Local checks cannot certify cloud admission, policy enforcement, hosted routing,
native evaluation or the unpublished afternoon experience.
