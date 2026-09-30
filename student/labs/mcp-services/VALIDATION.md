# MCP backend validation

Execution date: **2026-09-30**. Scope: the two synthetic MCP backends, not the
complete afternoon student lab or a teacher showcase.

- FastMCP 4.0.5, Python 3.13.15; isolated approved-feed `uv.lock` resolved.
  A clean committed-source export, new virtualenv and `uv sync --frozen
  --no-cache` passed both complete local HTTP journeys on Windows.
- [Initial publication run](https://github.com/tkubica12/foundry-workshop/actions/runs/36741598603)
  built separate Linux images and tested every tool through their actual
  Docker HTTP endpoints before pushing immutable SHA tags.
- Both exact GHCR manifests were retrieved using anonymous registry tokens;
  Azure app configurations contain no registry credentials.
- A clean Azure deployment was observed in Sweden Central. ARM returned
  `environmentMode=Express`, `provisioningState=Succeeded`, HTTPS-only ingress,
  0.25 vCPU/0.5 GiB per app and min 0/max 1 replica.
- Workstation `verify.py` passed all **6 partner + 10 complaint tools** in
  modern and legacy modes: discovery, pagination, combined filters, POST/PUT,
  version conflicts, case updates, assignments, notes, all lifecycle branches,
  statistics, exact delete, expected errors and test-record cleanup.
  Initial remote run: 62.6 seconds; repeat-deployment run: 75.3 seconds.
- Repeat deployment retained the existing app/environment identities and
  passed the complete remote test again.
- `verify_reset.py --confirm` created a record in each deployed service,
  stopped/started both apps, verified both sentinel IDs no longer existed,
  confirmed exact 120/90 seed counts, and passed every remote tool again.
  Earlier post-reset runs exposed transport disconnections when reusing pooled
  HTTP connections; disabling verifier keepalive reuse resolved the exercised
  reset journey without retrying uncertain writes.
- Missing/incorrect bearer keys were rejected with 401 on MCP GET/POST/DELETE;
  the public health route exposes no records. The requested demo key remains
  in ignored `.env` and an Azure manual secret, never in source/image/state.
- Seven mocked automation tests cover ownership refusal, confirmation,
  cleanup pagination including an unrelated app on page two, exact deletion
  scope, cross-host pagination rejection and retained recovery markers.
  **Live cleanup was not run**: the requested live applications are retained.
  No live cleanup success or complete attendee-lab qualification is claimed.
- Independent security/destructive-safety and preparedness review found one
  material cleanup-pagination issue. It was repaired; an independent narrow
  re-review with the two-page mock reported no blocking/material issue.

The apps remain provisioned and can incur Azure compute/transfer charges.
The shared-key and volatile shared-memory model is for synthetic workshop use
only; restart or scale-to-zero can discard all edits. Operational commands,
reset/cleanup boundaries and recovery are in [README](README.md).
