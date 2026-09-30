# 0008. Mock MCP backends on Container Apps Express

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Workshop maintainer

## Context

The planned tools chapter needs independent partner and complaint services that
can be reached from a professional builder's workstation and agent platform.
The requested contract is Python, synthetic data only, two separate public
GHCR images, application-level fixed-key authentication and Azure Container
Apps Express. No database or durable store is allowed.

Express supports Sweden Central, public images, manual secrets, HTTPS ingress,
single revisions and scale-to-zero, but not Easy Auth or session affinity.
Verified against the [Express feature matrix](https://learn.microsoft.com/azure/container-apps/express-overview)
and [2026-07-01 environment schema](https://learn.microsoft.com/azure/templates/microsoft.app/2026-07-01/managedenvironments)
on the decision date. FastMCP 4.0.5 is available in the approved Python feed;
its client/server negotiate modern and legacy MCP eras.

## Decision drivers

- Exercise real tool discovery, structured validation and remote CRUD.
- Avoid hidden database state, credentials in images and workstation Docker.
- Keep synthetic environments resettable and cloud scope explicit.
- Retain interoperability with older Streamable HTTP clients.

## Options considered

### Option A - two images, in-memory stores, Express

Matches the requested isolation. Deterministic generated fixtures simplify
reset and reproduction. Volatile memory prevents durable or horizontally
scaled use.

### Option B - one combined server

Smaller deployment surface but does not match the explicit two-image decision.

### Option C - database-backed or standard Container Apps

Would improve durability or infrastructure flexibility, but violates the
requested mock-only/Express constraints and increases setup overhead.

## Decision

Use two FastMCP 4.0.5 services with code-generated 120 partners and 90
complaints, schema validation, version-checked mutations and explicit lifecycle
rules. Store records only in process memory under locks. Use one process,
one worker and max one replica for each app. Expose authenticated `/mcp`
with a health-only public route. Use stateless Streamable HTTP and exercise
both modern and legacy negotiation.

Publish using GitHub Actions `GITHUB_TOKEN`; allow anonymous pulling only after
both GHCR packages are public. Pin runtime dependencies and export hashed
requirements from the isolated approved-feed lock. Deploy with ARM from a
local script, verifying actual Express mode and ownership tags.

## Consequences

Restart, redeployment or scale-to-zero can discard all edits and reload fixtures.
Clients share a single synthetic store and cannot assume independent sessions.
Complaint partner references are not cross-service foreign keys; the client
must verify partner eligibility. A shared API key grants every tool and is a
demo-only authorization model. Azure compute/transfer costs remain applicable.
Real records, production use and durability claims are explicitly excluded.

## Assumptions and revisit triggers

- Mock reset behavior is acceptable; requiring durable edits reopens storage.
- A shared key is acceptable only for a restricted synthetic workshop;
  per-user authorization or real data requires a different auth design.
- No need for more than one replica; throughput/HA requirements reopen storage.
- Supported Express features and region remain available; requalify on changes.
- The complete student tools lab is separately authored and qualified.

## Validation

`scripts/test_local.py` starts clean processes and exercises all 16 tools via
HTTP in modern and legacy modes, including auth rejection, filtering,
pagination, optimistic concurrency, complaint transitions and test cleanup.
The publication workflow repeats the journey against both built Linux images.
`scripts/verify.py` uses the same exact journey against deployed HTTPS endpoints
from the operator workstation. Deployment checks anonymous GHCR manifests and
actual ARM Express mode. Live execution/review evidence is recorded separately
in the backend's operational validation record, not inferred from this ADR.
