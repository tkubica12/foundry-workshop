# 0006. Publish a customer-neutral one-day workshop with a fresh history

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Workshop owner

## Context

The workshop is becoming a public, reusable learning resource for professional
builders. Its source includes existing local work on build and evaluation labs,
teacher automation, fixtures and a self-contained HTML runtime. Customer-specific
names, environment captures and private continuation records must not become
dependencies of a public clone.

## Decision drivers

- Preserve usable current work, including changes not yet committed.
- Publish no customer branding, original environment identity or private state.
- Remove UI screenshots and maintain precise text-only click instructions.
- Keep the original checkout, remote and historical evidence unchanged.
- Focus the roadmap and target timetable on one workshop day.
- Distinguish a development baseline from a qualified live delivery.

## Options considered

### Option A - Publish the original repository and commit history

Simple, but current-file cleanup does not remove customer context or operational
evidence from earlier commits. Rejected.

### Option B - Export current nonignored source into a new repository

Preserve existing working files, omit deleted files, private state and Git history,
sanitize the exported source, and start with one initial commit.
Chosen. Original historical material remains in the original repository, not here.

### Option C - Rebuild the workshop from empty templates

Eliminates inherited context but discards functioning labs, fixtures and checks.
It adds learning-design and delivery risk without helping the publication goal.

## Decision

Create the public `tkubica12/foundry-workshop` repository with a fresh history.
Keep only current nonignored source and authored assets. Use generic
workshop identifiers and fictional store codes consistently in code, tests and
fixtures. Rename ownership markers as well as display names; do not migrate,
adopt or clean up resources created by the original workshop.

Remove all UI screenshots and galleries, including embedded or unused copies.
Maintain precise menu paths, control labels, field values and expected results
in the lab text. Browser captures used for local validation stay in ignored
evidence, not the attendee publication. Preserve copyright and third-party
runtime license notices.

Keep text in LF form through `.gitattributes` so fixture integrity hashes and
download bytes survive a fresh checkout on Windows and other platforms.

Re-express inherited ADRs where their justification depended on private deployment
evidence. Preserve their numbers and architectural decisions, but do not publish
private request IDs, endpoints or inaccessible evidence paths. This supersedes
the archive-distribution assumptions of ADR 0005, not its labs-first publication
decision. Original unsanitized records are not part of this repository.

Set a single-day target timetable. Labs 2 and 3 are published; tools, knowledge,
hosted-specialist hands-on work and opening/closing showcases remain explicit
roadmap work. The development baseline does not promise a complete rehearsed day.

## Consequences

A fresh clone contains the working content and its checks without requiring the
original repository or an author's machine. Private configuration and cloud state
remain excluded. Prior cloud qualification does not transfer to renamed resources
or changed prompts. Operators must supply their own contracts and perform a clean
live rehearsal before delivery.

Existing browser preferences intentionally start a new customer-neutral namespace.
No migration reads the original namespace. Original state remains in the original
browser origin and can still be exported using the original material.

## Assumptions and revisit triggers

- The audience remains general professional builders. Customer adaptations belong
  outside the reusable core and need their own publication review.
- The workshop fits one day. Revisit scope, not the day length, if rehearsal shows
  insufficient recovery time; move optional depth out of the core path.
- Text-only instructions replace UI captures. Revise click paths and requalify
  the attendee journey if portal controls change.
- Requalify live access, quotas, models and feature availability for each delivery.

## Validation

Run the public-source boundary tests, guarded offline lifecycle tests and the
browser/content/export collection against the exported checkout. Verify
the absence of UI captures, review the one-day learning sequence and resource-ownership changes
independently, then verify the public remote and its one-commit history.

Current evidence and limits are recorded in `teacher/VALIDATION.md`. These checks
do not deploy Azure resources or certify the unpublished afternoon labs.
