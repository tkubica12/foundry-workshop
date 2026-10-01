# 0013. LangGraph Hosted Agent with an immutable GHCR image

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Workshop owner and implementation agent

## Context

Lab 6 is planned as managed Memory and remains the last mandatory lab.
Lab 7 is an optional code-first Hosted Agent, followed by optional Teams
publication in Lab 8. The hosted specialist must reuse the synthetic MCP
services from Lab 4 rather than create a second business backend.

The current Hosted Agent runtime uses the Responses protocol on port 8088.
The older framework-specific agentserver adapter is retired. The supported
`langchain-azure-ai` hosting integration accepts a compiled LangGraph, exposes
interrupts as Responses approval requests, and provides user-isolated Foundry
checkpoint storage. References consulted on 2026-10-01:

- [LangChain/LangGraph hosting](https://learn.microsoft.com/azure/foundry/how-to/develop/langchain-hosted-agents)
- [Hosted Agent deployment](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent)
- [Runtime migration](https://learn.microsoft.com/azure/foundry/agents/how-to/migrate-hosted-agent-preview)
- [Hosted Agent tracing](https://learn.microsoft.com/azure/foundry/observability/quickstarts/quickstart-tracing-hosted-agent)
- [ACR image import](https://learn.microsoft.com/azure/container-registry/container-registry-import-images)

## Decision drivers

- Keep the optional lab focused on code, approvals and observability.
- Reuse seven curated tools and existing model deployments.
- Protect shared seed records even against an adversarial user instruction.
- Preserve interrupted state across hosted restarts and isolate conversations.
- Produce one reproducible image through GitHub Actions, not a local Docker daemon.
- Test anonymous GHCR deployment before introducing another registry.
- Never commit credential material or real environment identifiers.

## Options considered

### Option A - Current Responses host and LangGraph

Use `langchain-azure-ai[hosting,opentelemetry]`, LangChain's `create_agent`
factory (which builds a LangGraph), MCP adapters and FoundryCheckpointSaver.
This avoids reimplementing the Responses protocol and checkpoint recovery.

### Option B - Retired framework-specific adapter

The older `azure-ai-agentserver-langgraph` integration does not target the
current runtime. It is not selected.

### Option C - A registry and rebuilt image for every seat

This duplicates infrastructure, creates extra permissions and can yield
different binaries. It is not selected.

## Decision

Client delivery is extended by [ADR 0014](0014-ephemeral-cloud-shell-rest-lab.md):
the attendee path uses ephemeral Cloud Shell and Azure CLI REST; the runtime
and image decisions here remain unchanged.

Use Option A. Pin dependencies resolved through the approved package feed.
Discover the seven existing tools and reject missing or duplicate contracts.
Require a checkpointed runtime approval before every read. Expose the shared
tool inventory but deny all three mutation tools before any MCP execution:
Lab 7 intentionally does not repeat Lab 4's write exercise.

Prefer an existing version-pinned toolbox with refreshed Entra authentication.
Support direct use of the same two existing MCP services only with an explicit
operator configuration and a platform-resolved Foundry credential connection.
Never put a literal key in a published image or deployment definition.

The host owns the telemetry exporter; the LangChain callback shares the
OpenTelemetry provider and traces graph, model and tool work. Synthetic
message-content capture is explicit, not a production default.

Publish Linux/amd64 images to public GHCR with a commit tag and consume the
anonymous-pull-verified digest. Try that exact image in Foundry first. Only a
conclusive registry incompatibility permits a single separately scoped shared
ACR import of the same digest, without rebuilding.

Use private per-seat configuration and ownership receipts. Do not retry
ambiguous creates. Cleanup deletes only the recorded immutable version,
never the parent agent, another version, shared connections, roles or backends.

## Consequences

Approval adds deliberate interaction to the read path. Writes are not an
extension hidden behind a system prompt; they require a separate future
ownership design and qualification. Hosted checkpoints and monitoring data
have independent retention responsibilities.

Package visibility, image activation, runtime identity permissions and trace
viewer permissions are separate failure boundaries. Offline protocol success
does not establish live Foundry or attendee readiness.

## Assumptions and revisit triggers

- The existing toolbox exposes exactly the seven business tools. Revisit if its
  names, approval contract or authentication behavior changes.
- The runtime remains compatible with Responses 2.0.0 and the pinned hosting
  libraries. Requalify after any SDK/runtime upgrade.
- GHCR anonymous pulls work for the selected runtime and region. If an actual
  registry-specific failure disproves this, qualify the shared ACR import path.
- Revisit read-only scope only if a new lab outcome requires writes; require
  synthetic record ownership, version checks and recovery first.
- Revisit the 45-minute optional-lab target after fresh attendee timing evidence.

## Validation

Offline tests exercise the actual HTTP Responses host, approve/reject continuation,
tool inventory, write denial, uncertain creates, locks and version-only cleanup.
An independent safety review identified and then verified repair of a
parent-deletion race. Live operator MCP discovery returned the seven expected
tools. The published, anonymous-pull-verified GHCR digest activated directly in
two isolated hosted instances. Their approved answers matched actual tool
results; rejected chains executed no tool. Correlated hosting, graph, model
and tool spans were observed in Application Insights. Both immutable versions
were cleaned up and verified absent. Attendee roles, native trace viewers,
room concurrency and the learning timebox remain separate qualification gates
recorded in the lab's operational validation record.
