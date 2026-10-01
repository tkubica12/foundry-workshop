# 0010. Curated toolbox and isolated lab actions

- **Status:** Superseded by [0011](0011-browser-authored-toolboxes.md)
- **Date:** 2026-09-30
- **Deciders:** Workshop maintainers

## Context

Lab 4 follows agent construction and evaluation in the one-day agenda. Two
synthetic instrument-domain MCP services already exist, exposing 16 tools through
authenticated Streamable HTTP. Their memory and bearer key are shared, and writes
are volatile. The tools chapter has 75 minutes, including demonstration and
architecture discussion. The requested outcome is an actual agent action with
observable MCP calls, not just successful server registration.

Microsoft Learn documents toolbox curation/versioning, MCP-compatible consumption,
stored connection authentication and runtime-enforced approvals. Live API testing
on 2026-09-30 confirmed filtered toolbox discovery, prefixed tool names,
caller-Entra-token consumption and approval continuation responses. Portal login
was explicitly deferred, so no observed one-click portal authoring is assumed.

## Decision drivers

- Preserve 15 core minutes for inspecting exact tool-call evidence.
- Teach connection, toolbox and agent boundaries without backend setup latency.
- Avoid concurrent modification of shared seed cases.
- Show a meaningful, versioned write and independently verify it.
- Keep credentials and private environment identifiers out of public material.

## Options considered

### Option A - two directly attached MCP servers

Simpler initial attachment, but duplicated configuration and all 16 backend
capabilities unless every attachment is separately restricted. It does not teach
the reusable toolbox boundary.

### Option B - curate a toolbox live from scratch

Good authoring depth, but toolbox management exposure, identity permissions and
credential setup add delivery risk. A precise one-click portal path is not yet
rehearsed. Installing SDK/tooling during this browser-first lab consumes time
without improving the main action/observability outcome.

### Option C - prepared per-seat toolbox with one owned action

Register and curate before class using explicit operator automation. Inspect
those stages, attach one toolbox, investigate, create an isolated case, approve
assignment, inspect traces. Optional depth adds a note or approval-denial check.

## Decision

Choose C. Expose two partner reads and five complaint tools; exclude deletion,
partner writes, lifecycle transitions and arbitrary updates. Require every call
to be approved at the runtime boundary. Preserve the Lab 3 version and create a
new version with tool-aware instructions, not the earlier no-tools instructions.

Use an owned generated complaint and unique seat/run marker, not a seed mutation.
Verify partner eligibility across services, refresh the complaint version before
writing, and read back afterward. Instructions and the marker are teaching
constraints, not server-enforced authorization or uniqueness.

## Consequences

The core is 50 minutes with recovery/discussion margin. Seat preparation requires
authorized project and telemetry access and a rehearsed attachment surface.
Operator automation stores secrets only in project connections and receipts only
under ignored `.workshop`. Repeats reuse identical owned resources; differences
fail instead of changing defaults. Cleanup is exact and facilitator-owned.

Shared memory can reset, and approval continuations can hit token-rate limits.
Missing state requires a new run marker; an uncertain write requires inspection,
not a blind retry. Traces can contain synthetic data and remain private.
Production requires durable storage, scoped server-side authorization,
idempotency and cross-service integrity; the workshop backend supplies none.

## Assumptions and revisit triggers

- A prepared toolbox, an MCP-capable model and telemetry access exist per seat.
  If attendee permissions or portal attachment cannot be qualified, block release
  rather than silently substituting direct-server attachment.
- Every call is approved by the consuming runtime. If it ignores approval
  metadata, stop writes and select a runtime with verified enforcement.
- The full exercise remains within the volatile memory lifetime. If class
  rehearsal loses cases or concurrency becomes unsafe, use isolated per-seat
  backends or durable storage before delivery.
- Revisit live toolbox authoring only when its actual attendee-visible flow is
  stable and measured within the timebox.

## Validation

Clean local HTTP and deployed MCP journeys verify the exact read/create/assign/
note/readback path, stale-version refusal and exact generated-record cleanup.
Live Foundry testing verifies registration, filtered toolbox creation, identity
connection, agent tool calls and platform approvals; actual ingested telemetry
includes toolbox discovery and tool execution spans. Repeat seat preparation
reuses the same default version.

HTML browser validation checks all canonical palettes, 1280x720 and 1920x1080,
offline reading, no-JavaScript content and print. Review and remaining live
qualification boundaries are recorded in the lab's operational VALIDATION.md.
Portal click paths and attendee-role reproduction are not inferred from API tests.
