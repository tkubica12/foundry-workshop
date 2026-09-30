# 0005. Publish a labs-first workshop

- **Status:** Accepted
- **Date:** 2026-09-18
- **Deciders:** Workshop owner

The labs-first publication decision remains accepted. Archive distribution and
private evidence references and screenshot-preservation requirements are superseded by
[ADR 0006](0006-customer-neutral-public-baseline.md). The public clone contains
only current source, not retired material or original Git history.

## Context

The workshop owner approved replacing the slide-led public site and five generic
architecture references with a small lab entry point. The priority is a progressive
hands-on journey: build, evaluate, add tools, add knowledge, then add a hosted
specialist. Existing speaker-first material reflects an earlier sequence and must
not imply that future labs or live environments are already available.

## Decision drivers

- Make the next implemented exercise easy to find, without a storytelling homepage.
- Preserve the reviewed Chapter 2 exercise, all teacher demo source, shared
  synthetic fixtures and required document assets. ADR 0006 replaces UI screenshots
  with precise textual steps in the public baseline.
- Keep unpublished plans and retired material outside the served `docs` tree.
- Preserve prior decisions and exercise state rather than silently migrating them.
- Retain useful generic checks while removing retired artifacts from active inventory.

## Options considered

### Option A - Keep the decks and references in public navigation

This preserves old links but competes with the new lab sequence, enlarges the
maintenance surface and risks presenting plans as implemented hands-on work.

### Option B - Archive explicitly selected files outside publication

Move the eight existing slide HTML files and five generic references into a
gitignored local archive, preserving paths and bytes. Copy the original plan and
agenda there before shortening them. Publish a minimal index linking Labs 2 and 3.
Keep future Labs 4 and 5 as plain text, not dead links. This is the chosen option.

### Option C - Delete historical material and replace the runtime

This loses local recovery context and adds unrelated migration risk to the
preserved lab and passport. A new document runtime is unnecessary.

## Decision

Choose Option B. The archive is `.workshop/archive/2026-09-18-labs-first/`, outside
`docs` and ignored by Git. A manifest records original paths and SHA-256 hashes.
Archive only the enumerated files, never recursively delete a broad directory.
The archive is local working history, not a distributable site or a backup shared
with future clones; tracked history remains the durable historical source.

Keep the canonical HTML-docs runtime, templates and existing assets. The index is
reading-only, with immediately visible links and a persistent theme control.
Retain the learning passport because Chapter 2 links to it; do not change its
storage schema, field names or import/export behavior. Existing passport checkpoint
labels remain worksheet identifiers, not a claim that the new sequence is complete.

Archive the retired deck and reference-specific test modules alongside their
artifacts. Keep generic HTML, navigation, rendering, export, accessibility,
template runtime, passport and fixture coverage active. New publication checks
must reject accidental reintroduction of retired pages and broken active links.

This changes the publication-scope decision in [ADR 0004](0004-canonical-html-docs-ui.md)
to retain all seven decks, not its accepted canonical-runtime decision. Its
assumption that the earlier deck sequence remains the live agenda has changed.
ADRs 0001–0003 and the remainder of ADR 0004 remain accepted historical decisions.

## Consequences

The public site becomes smaller and easier to navigate. Retired URLs are intentionally
not served; no redirects or copied references recreate that publication surface.
The local archive may need restoration from Git history on another machine.

Lab 3 must exist before publication validation passes. Future labs are explicitly
unavailable. Showcase reuse, LangGraph hosting, Teams and Autopilot are roadmap
items, not newly verified deployments. No cloud resources, permissions, secrets,
dependencies or demo automation change as part of this publication decision.

## Assumptions and revisit triggers

- Labs are the primary attendee navigation unit. Revisit if a rehearsed delivery
  requires a separate speaker-first deck with a distinct, useful narrative.
- Rebuild references only for an observed learner need not met by lab explanations;
  require current sources, stable links and educator/browser review before publishing.
- Publish each future lab only after its guide, starting state, recovery path and
  exact journey have been tested. A roadmap title alone is not a publishable lab.
- Revisit archive distribution if another delivery team needs historical working
  files without access to repository history.
- Continue serving only `docs`; serving the repository root would expose private
  operational state regardless of this simplified navigation.

## Validation

The archive operation compares source and destination SHA-256 hashes and verifies
Git ignore coverage. Active tests cover HTML structure, local links, no external
runtime dependencies, light/dark layouts, keyboard navigation, no-JavaScript reading,
isolated exports and existing passport state behavior.

Current run results and remaining integration gates are recorded in
`teacher/VALIDATION.md`. Original archive manifests and private evidence are
not distributed. Local publication checks do not qualify a live cloud lab or
teacher demonstration.
