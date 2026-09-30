# MCP backend validation

Execution date: **2026-09-30**. Scope: the two synthetic MCP backends, not the
complete afternoon student lab or a teacher showcase.

## Musical instrument domain

The business vocabulary is Aster Vale Instruments, aligned with the fictional
20-model workshop instrument catalogue. Technical deployment/authentication,
tool names, endpoints, runtime versions and container layout are retained.
Local HTTP journeys passed all 16 tools in both protocol eras, covering every
instrument family, partner service, complaint category, transaction type and
serial lookup, domain statistics, model coverage and seeded assignment
eligibility. The seven existing Azure safety mocks also passed.
An independent domain/implementation/Educator review inspected the actual
backend, verifier, operator contract and session Canvas examples, checked all
20 model identities/families and 120/90 fixture records, and reported no
blocking or material finding.

[Music-domain publication run](https://github.com/tkubica12/foundry-workshop/actions/runs/36752675501)
passed both clean-process HTTP tests and both actual Linux Docker image
journeys, then published and anonymously verified immutable tags for source
commit `2b6f70655ff40f3835d6a33b88631385ad22a947`.
Those exact images were deployed to the existing Express applications without
changing their URLs, authentication, registry access or 0/1 scaling settings.
The full workstation remote verifier passed modern and legacy journeys in
97.3 seconds. Reset qualification also passed: generated sentinel writes
disappeared, exact 120/90 fixture counts returned and both complete remote
journeys passed again.

The refreshed session-only Canvas loaded the new live schemas and music
examples. A real Playwright browser journey called **all 16 MCP tools** through
the UI, checked musical product/family/serial/transaction fields, chained
record versions, and removed its generated records. Invalid JSON and schema
values, mutation confirmation, CSRF rejection, light/dark/mobile layout and
keyboard focus passed. Screenshots remain private session evidence, not
published assets. The Canvas is not an attendee guide or a committed runtime
dependency.

## Original technical qualification

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
