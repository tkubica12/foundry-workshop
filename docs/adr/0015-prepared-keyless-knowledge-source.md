# 0015. Prepare keyless knowledge ingestion before the lab

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Workshop maintainers

## Context

Lab 5 must compare an unchanged agent before and after adding 20 synthetic PDF
dossiers within a 45-minute core. Attendee upload failures and policy-disabled
API keys made operator-only qualification insufficient. A new student identity
completed direct file ingestion, KB authoring and cited retrieval, but bulk
upload was throttled at 12/20 and needed two failed-file-only retries.
Search provisioning and embedding quota also blocked clean deployment until
capacity or quota became available.

## Decision drivers

- Preserve grounding, citation inspection and the balanced before/after evaluation.
- Keep provisioning, permission propagation and throttled ingestion off the timebox.
- Use Entra identities with local authentication disabled; never require shared-group Owner.
- Qualify regional features separately from live capacity and image extraction.

## Options considered

### Option A - Prepared direct-file source

Prepare an assigned Search service, model access and all 20 processed files.
The attendee selects the existing source, creates a KB and attaches it to the
baseline agent. No customer-provided Storage account is needed.

### Option B - Native bulk upload during the core

The portal supports keyless direct files, but the observed 20-file operation
required two retries. It remains a useful extension, not a deterministic
classroom dependency.

### Option C - Personal or shared Blob storage

Personal storage places role-assignment authority in the attendee's group,
but adds account/container setup, upload, networking and Search identity access.
Shared storage still needs an operator to grant each newly created Search
identity access. Prior Blob rehearsal was blocked by network policy; neither
variant is a qualified simpler fallback.

## Decision

Use a prepared minimal-extraction direct-file source for the core. Require
Project Managed Identity for the Foundry connection, Search's system identity
for model calls, and explicit data-plane permissions. Keep native upload and
standard/Content Understanding extraction as separate extensions.

The observed regional combination is Basic Search in West Europe with Foundry
models in Sweden Central. Operators must approve geography and cost, verify
admission before delivery and supply the prepared fallback. Do not infer
agentic retrieval support from semantic ranking or successful Search creation:
Spain Central lacks agentic retrieval and AI enrichment in the current matrix.

## Consequences

The hands-on outcome remains an attendee-authored KB, verified cited answer
and comparison, rather than infrastructure troubleshooting. Operators take on
source preparation, identity assignments, quota checks and exact-scope cleanup.
Basic remains paid while provisioned. Shared model resources are possible only
when the operator authorizes every prepared Search identity in advance.

Minimal extraction deliberately preserves image-only failures for discussion.
Standard extraction can verbalize images keylessly but needs separate operator
configuration and carries extra charges. A one-document success is not a
full-corpus or all-region guarantee.

## Assumptions and revisit triggers

- The learning outcome is grounding and evaluation, not Storage administration.
  Revisit if ingestion authoring becomes a required core objective.
- Prepared source selection remains available to the assigned attendee identity.
  Requalify when portal behavior, RBAC, Search APIs or policies change.
- West Europe/Sweden Central geography is approved for the synthetic workshop.
  Revisit if residency, regional support, quotas or admission change.
- Native upload remains variable under bulk/concurrent load. Revisit only after
  a complete room rehearsal demonstrates bounded reliable ingestion.

## Validation

The 2026-10-01 student rehearsal used a new identity with personal-group Owner,
Foundry User and Search Index Data Contributor, not shared-group Owner. It
verified native creation/upload, two targeted retries, 20 filenames/300 chunks,
stored 1,536-dimensional vectors, live query vectorization, and a completed
MCP-backed answer with actual matching acoustic-guitar citations.
The same identity selected the existing 20-file source, created a second KB
and attached it to its existing agent; a fresh chat returned the expected facts.

An operator standard-extraction probe omitted all API keys and used the
Search system identity. The raster shipment chart yielded `2022 -> 502`,
and a matching cited answer. Only one document was tested.
Private evidence stays ignored; concise boundaries are recorded in
[Lab 5 qualification](../../student/labs/knowledge-base/VALIDATION.md).
Least-privilege authoring, full-room concurrency and complete delivery timing
remain explicit gates rather than inferred successes.
