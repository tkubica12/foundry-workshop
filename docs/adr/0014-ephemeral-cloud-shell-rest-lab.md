# 0014. Deploy the optional hosted lab through ephemeral Cloud Shell REST

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Workshop owner and implementation agent

## Context

The owner selected a no-local-install attendee path after a live investigation.
ADR [0013](0013-langgraph-hosted-agent-and-ghcr.md) remains accepted for the
runtime, read approvals, telemetry and immutable GHCR delivery. This decision
changes its client delivery surface, not the agent or image build.

Official references consulted on 2026-10-01:

- [Hosted Agent REST deployment](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent)
- [Ephemeral Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/get-started/ephemeral)
- [Cloud Shell upload/download and session controls](https://learn.microsoft.com/azure/cloud-shell/using-the-shell-window)

An isolated operator investigation used real ephemeral Cloud Shell, Azure
CLI 2.90.0 and PowerShell 7.6.5 on Azure Linux 3.0. API `v1` activated the
existing public GHCR digest without Python SDK calls or preview headers.
Approved reads, explicit rejection and correlated Application Insights traces
passed. The programmatic terminal needed an in-memory credential bridge from
the authorized local login; this did not qualify browser-only first login.

## Decision drivers

- Remove local language runtimes and package restoration from the core lab.
- Preserve the existing code-first learning outcome, image and business tools.
- Make individual tool approvals and correlated evidence inspectable.
- Keep lifecycle ownership checks, non-replayed uncertain operations and
  version-only cleanup at least as strict as the SDK operator path.
- Recover from ephemeral file loss without widening destructive scope.

## Options considered

### Option A - Azure CLI REST in ephemeral Cloud Shell

Use preinstalled Linux PowerShell and Git to run a small checked wrapper around
`az rest`. No storage account or attendee package installation is needed.
Explicit download/restore of private receipts is required.

### Option B - Python SDK in a prepared local environment

Keep the prior operator client. It has proven behavior but adds Python, uv,
dependency restoration and machine-state variance. Retain it for operators,
not as the attendee core path.

### Option C - Azure Developer CLI agent tooling

The inspected agent extension is preview and handles a broader build, registry
and RBAC lifecycle. That is unnecessary for an existing image and prepared
project. It was not qualified end to end and is not selected.

## Decision

Choose Option A. Use `scripts/lab07.ps1` with Azure CLI REST API `v1` and a
version-pinned Responses `2.0.0` image. Publish image builds only through the
existing GitHub Actions workflow; do not build containers in Cloud Shell.
Keep the HTML guide reading-only and optional.

Validate private assignment, active subscription, fingerprint, immutable digest
and live ownership. Persist intent before non-retried creates and Responses
POSTs. Serialize seat operations. Recover uncertain creates by matching one
live version, never by replay. Approve only one reviewed current ID.

Download the private JSON receipt archive after deployment, turns and cleanup.
Restore the latest trusted archive into an empty directory. If evidence is lost
or older than a later POST, stop for facilitator inspection. Do not transfer
tokens, locks or secrets in a recovery archive.

## Consequences

The deployment client needs no attendee-installed Python, uv, Docker or SDK.
Python stays inside the hosted image. Model/tool/runtime and trace-viewer
permissions remain separate from deployment access.

Ephemeral session termination does not delete the hosted agent. File loss,
portal token acquisition and stale backups become explicit recovery boundaries.
The guide provides assigned-tenant `az login --scope` recovery but does not
permit policy bypass or an administrator identity.

Version-only DELETE never targets the parent. Observation of the last-version
cleanup returned NotFound for the parent as well; retention of a visible empty
parent shell is not guaranteed. Monitoring/checkpoint data has independent
retention.

## Assumptions and revisit triggers

- Cloud Shell includes PowerShell 7, Azure CLI and Git and the provider is
  registered by the facilitator. Revisit if attendee policy prevents access.
- An approved browser credential path can acquire the Foundry audience.
  Requalify assigned-tenant authentication before a room delivery.
- The public immutable image and Responses protocol remain compatible.
  Requalify after runtime/API/image changes.
- Private receipt downloads/restores are permitted on attendee machines.
  If policy forbids them, prepare an approved durable per-seat alternative.
- Revisit the 45-minute target after a fresh attendee and room rehearsal;
  operator call durations do not qualify learning or portal timing.

## Validation

The original REST investigation deployed one isolated version, consumed six
Responses POSTs and captured 398 correlated telemetry rows across five
meaningful turns. Two approved reads had actual results and parent linkage;
the rejected continuation had no successful tool execution. Version absence
and repeated cleanup passed; the ephemeral console was subsequently verified
absent. No registry, permission or shared-resource changes were made.

The maintained wrapper adds regression checks and independent review evidence
recorded in [Lab 07 validation](../../student/labs/hosted-agent/VALIDATION.md).
Two additional maintained-client seats completed ten Responses POSTs, actual
correlated traces, trusted archive restore and owned-version/repeated cleanup.
Independent learning, safety and Student live-path reviews found no remaining
blocking or material issue in that exercised scope.
Keep browser-only authentication, native trace viewing, attendee roles and
room/timebox qualification distinct from programmatic Cloud Shell testing.
