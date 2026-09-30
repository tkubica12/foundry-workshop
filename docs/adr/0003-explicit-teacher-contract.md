# 0003. Resolve the teacher environment from an explicit nonsecret contract

- **Status:** Superseded by [0007](0007-focus-repository-on-published-labs.md)
- **Date:** 2026-09-16
- **Deciders:** workshop engineering, workshop delivery coordinator

ADR 0007 removed this teacher-demo implementation from the published-labs
repository. Paths below identify historical source locations and are not
expected to resolve in the current tree.

## Context

The Chapter 2 teacher demo needs a project, model route, tenant and observability
resource IDs before it can operate. Its former implicit resolver called
`uv run labctl status --prefix <prefix>` in the external platform repository.
The 2026-09-15 read-only feasibility inspection found that this command loads
`secrets\credentials.json` through `cli.py:_context` and calls
`TerraformRunner.outputs`, whose initialization includes `terraform init
-reconfigure` and ACL work. A command named `status` therefore crossed secret
and infrastructure boundaries before the demo's requested operation began.

The accepted implementation made that dependency explicit. Its historical
source of truth was
`teacher/demos/build-host-agent/scripts/demo.py` (`build_parser`,
`_contract_for`, `parse_contract`, `load_contract`) together with
`teacher/demos/build-host-agent/OPERATOR.md`.
The external inspection explains the legacy risk; it is not evidence that every
future `labctl` version has identical behavior.

This public baseline does not include the external platform checkout or its
inspection evidence. Supply your own explicit contract; independently authorize
and inspect any optional external resolver before using it.

This decision concerns teacher input resolution, not the attendee teaching
surface. [ADR 0002](0002-chapter-2-lab-is-portal-only.md) remains unchanged:
the Chapter 2 attendee lab is portal-only and the scored harness is teacher
material. Historical live evidence in earlier records does not certify a
rebuilt environment or the current attendee identity.

## Decision drivers

- Resolve required configuration without hidden platform setup or secret reads.
- Fail visibly on missing or inconsistent explicit input, before client use.
- Keep platform authorization separate from teacher demonstration authorization.
- Preserve an intentional compatibility path for existing platform operators.
- Separate local contract proof from live hosting and actual-seat qualification.

## Options considered

### Option A - retain implicit platform status

Convenient for an operator whose external checkout is already configured, but
depends on its tooling, credentials and Terraform initialization. It cannot
satisfy a local-only contract check and hides side effects behind discovery.

### Option B - explicit nonsecret JSON with opt-in legacy resolution

Require an operator-supplied file, validate it locally, and retain the old
resolver only behind a mutually exclusive CLI switch. This adds an explicit
handoff and a stale-configuration risk but makes the boundary inspectable.

### Option C - remove the platform resolver entirely

Eliminates that compatibility risk but breaks existing authorized operator
flows unnecessarily. Reconsider removal once those flows no longer need it.

## Decision

Choose Option B. Use `--contract-file` for the teacher demo. The JSON contains
an explicit `tenant_id` and `platform_outputs` with these required strings:

- `teacher_project_endpoint`
- `teacher_project_id`
- `teacher_foundry_id`
- `teacher_model_reference`
- `teacher_application_insights_id`
- `teacher_log_analytics_workspace_id`

Required strings cannot be null, empty, padded or contain control characters.
Resource IDs must have the expected types and share the teacher subscription;
the Foundry account must parent the project. The endpoint must be a
credential-free HTTPS project URL matching the project name, without query
or fragment. These are structural checks, not service existence or access checks.
The operator must supply nonsecret values; the parser is not a general secret
scanner or a contract exporter.

Missing, unreadable or incomplete explicit input fails without falling back to
ambient tenant values or external status. `--resolve-platform` is the deliberate
legacy alternative, with `--lab-repo` and `--prefix` selecting its scope.
`--contract-file` and `--resolve-platform` cannot be combined. The compatibility
switch does not grant authorization: obtain separate platform approval before
using it. Do not present it as read-only.

`contract --contract-file <file>` parses and prints the contract locally.
`preflight --contract-file <file>` additionally checks Azure CLI identity,
obtains a token and lists agents; it is not an offline check, although it does
not perform inference or create resources. Other lifecycle commands retain their
documented cloud, inference, state and cleanup effects.

Optional Memory additionally needs `teacher_memory_chat_model` and
`teacher_memory_embedding_model` (the parser also accepts the corresponding
`*_deployment_name` aliases). `memory-fallback` bypasses contract resolution
and requires an existing dated successful local recording. It fails when that
recording is absent rather than inventing a current result.

The optional scored harness uses a different schema and `--contract`, not
`--contract-file`. An explicit harness file uses only its own values and explicit
CLI overrides; absent or incomplete files never fall back to a machine seat file.
Legacy no-file harness resolution remains documented in
the historical `teacher/demos/build-host-agent/harness/seat.py`.

## Consequences

Contract parsing is reproducible without the platform checkout or authorization
to initialize infrastructure. Operators must deliver and maintain a matching
nonsecret contract before rehearsal. No automatic exporter, deployment or
permission grant is introduced by this decision.

A structurally valid file can still point to unavailable or unauthorized
resources. Live preflight, deployment, exact showcase, route/trace attribution,
repeat deployment, reset and scoped cleanup remain separate qualification gates.
The explicit file neither reduces their permissions nor proves their results.

The local offline verifier runs only the six trusted Chapter 2 test modules,
with network/subprocess guards, dotenv disabled and synthetic per-test paths.
Browser/PDF checks run separately because they need child processes. This
guarded runner is not a security sandbox for untrusted code.

## Assumptions and revisit triggers

- The platform operator can supply and refresh nonsecret contract values.
  Revisit if manual handoff repeatedly produces stale or mismatched scope.
- The legacy resolver remains permission-sensitive. Reassess against actual
  source if `labctl` gains a documented, versioned, side-effect-free export.
- Revisit compatibility retention when all authorized delivery flows use files.
- Revisit the schema when project URL, resource hierarchy, model routing or
  observability requirements change; verify current APIs before implementation.
- A current actual-seat or teacher rehearsal failure reopens delivery
  qualification, not the portal-only decision by implication.

## Validation

The accepted Chapter 2 reliability change passed 265 guarded local tests.
An independent lifecycle/operator recheck passed those cases plus eight reviewer
probes (273 total), closing the explicit-file fallback and required-value
validation findings alongside the related lifecycle repairs.

The portable command and integration results above are historical evidence for
the removed implementation and are not distributed in this repository. They
covered parsing, isolation and mocked lifecycle behavior, not current teacher
deployment, hosted transport, routing, trace propagation, policy attribution,
attendee sign-in, licensing or room-concurrency readiness.
