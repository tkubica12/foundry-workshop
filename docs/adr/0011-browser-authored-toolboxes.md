# 0011. Browser-authored toolboxes from registered servers

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Workshop maintainers
- **Supersedes:** [0010](0010-curated-toolbox-and-isolated-lab-actions.md)

## Context

ADR 0010 chose prepared toolboxes while portal testing was deferred. The user
subsequently requested an actual Edge rehearsal and signed in to the authorized
test project. Observed controls now establish a browser-only authoring path:
Tools has a Toolboxes tab, Create toolbox, per-server configuration and Publish.
This changes the earlier uncertainty about authoring exposure; it does not
establish attendee-role access, room capacity or overall workshop readiness.

Registration uses Custom / Model Context Protocol (MCP) / Create, then the server
form and Connect. Connection names are limited to 27 characters. A toolbox exposes
its managed MCP endpoint but has no tested native one-click prompt-agent
attachment. The agent consumes it as another custom MCP connection using
Microsoft Entra / Agent Identity and audience https://ai.azure.com.

## Decision drivers

- Let the hands-on exercise teach actual curation, not just inspect a summary.
- Keep backend credentials and resource provisioning out of the attendee path.
- Preserve 15 minutes of exact trace inspection inside the 75-minute chapter.
- Retain scoped synthetic writes, runtime approval, version checks and readback.
- Base control labels on the observed portal, not inferred SDK capabilities.

## Options considered

### Option A - retain fully prepared toolboxes only

Reliable recovery path, but misses the meaningful browser authoring experience
now available. Retain this as the fallback, not the main exercise.

### Option B - register servers and author everything live

Teaches all boundaries but requires credential distribution and extra setup
permissions. Keep registration as a facilitator demonstration or explicitly
authorized extension; reuse prepared project connections for the core.

### Option C - prepared connections, attendee-authored toolbox

Create a per-seat toolbox from two registered connections, curate seven tools
and approvals, publish, attach the managed endpoint to the prior agent, then
execute and inspect the owned synthetic action.

## Decision

Choose C. The core target becomes 55 minutes: preparation 5, curation/attachment
15, read/create 10, assignment 10, traces 15. The remaining chapter time covers
demonstration, architecture and recovery. These are design targets, not measured
attendee completion times.

Use the observed comma-separated Allowed tools fields and Never auto-approve
tools on both inner servers and outer attachment. Every pending call uses
Approve / Approve once; persistent auto-approval is not part of this exercise.
Keep the original seven-tool allowlist, owned generated cases, eligibility checks,
current-version writes and independent readback from ADR 0010.

Use the existing full-seat preparation script as recovery. Its qualified
UserEntraToken consumer connection is an alternative to the UI's Agent Identity
connection, not an option claimed to exist in the portal Type dropdown.
Do not change roles or backend scaling implicitly.

## Consequences

No SDK installation is required during the browser core. Operator setup still
owns server credentials, runtime identity permissions, telemetry access and
capacity. Publishing exposes an unversioned consumer endpoint following the
default version; keep each seat's toolbox unchanged during the run.

One logical tool action can appear as an agent execute_tool span and a toolbox
tools/call span. Teach correlation rather than treating the displayed span count
as a count of repeated business mutations. The Input + Output and Metadata tabs
provide arguments, results and response/trace IDs.

Network errors and model-parameter mismatches are real qualification findings.
Never replay a write blindly; inspect state first. Keep the volatile-storage,
durability, server-side authorization and rate-window limitations from ADR 0010.

## Assumptions and revisit triggers

- The intended attendee can author toolboxes and the runtime identity can consume
  them. If either is missing, use the explicit prepared fallback or block release.
- The observed control labels remain available. Rehearse after portal changes.
- The full class journey fits the timebox and backend lifetime. If not, reduce
  optional depth or qualify isolated durable/stably running backends with explicit
  authorization; do not hide a keepalive or scaling change.
- Persistent approval is never enabled. If the runtime ignores the approval
  requirement, stop writes.

## Validation

The real signed-in Edge journey registered both MCP servers, published a filtered
toolbox, attached it through Microsoft Entra / Agent Identity, completed the
exact read-only prompt with approvals to both servers, and opened its actual
conversation, tool input/output and metadata in portal traces.

Creation, assignment, recovery and cleanup outcomes are recorded separately in
the lab's operational VALIDATION.md; do not infer their success from the topology.
The browser account is the authorized operator's account, not evidence of a
least-privilege attendee-role rehearsal.
