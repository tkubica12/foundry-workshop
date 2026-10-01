# 0009. Publish reading-only labs with HTML-docs 1.2

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Workshop owner

## Context

The owner requested a first browser-only lab for project creation and model
deployment, then explicitly selected HTML reading guides only for all labs:
no slides, sheet views or one-pagers. The installed HTML-docs skill is now
1.2.0, with new canonical accent pairs and print support.

This supersedes only ADR 0004's combined reading/presentation guidance for
labs and its older runtime palette. Its canonical-runtime, offline execution,
licensing and document-scoped preference decisions remain accepted. The
separate slide-deck authoring template remains available for teacher material.

## Decision drivers

- Keep a lab's essential instructions in one readable HTML source.
- Preserve stable anchors, copy/download behavior and existing exercise inputs.
- Adopt the explicitly requested canonical colors without patching upstream.
- Keep access, quota and latency qualification separate from local rendering.

## Options considered

### Option A - Keep lab slides and reskin only the old tokens

This contradicts the owner's view selection, retains duplicate summaries,
and leaves the runtime and validation contract on an older version.

### Option B - Upgrade the vendored runtime and make labs reading-only

Copy the installed 1.2.0 assets, synchronize canonical heads, remove lab slide
surfaces and slide assets, and retain the existing article interactions.
Update local regression contracts for four accent families and printing.

## Decision

Choose Option B. Published labs and the lab-guide template offer Read only.
Keep the PDF control as a browser print action, not a separate PDF deliverable.
No sheet view or standalone one-pager is authored.

Keep blue as the default. Preserve ADR 0004's owner-approved reader-selectable
canonical alternatives: red, green and yellow, one family at a time. The 1.2.0
light/dark pairs are copied from the installed skill, not manually recolored.
Existing orange preferences map to red through the canonical runtime.

Lab 1 is a manual portal learning outcome, not an environment automation
workflow. It creates one project and three deployments in an assigned resource
group. Shared subscription permissions, quota, feature enablement and provider
terms are facilitator prerequisites. It does not grant permissions or replace
Lab 2's explicitly different model and guardrail prerequisites.

## Consequences

Lab reading no longer loads presentation code or maintains unused speaking
summaries. All published workshop pages and authoring templates use one
versioned local runtime. Existing Lab 2/3 prompts, datasets, deep links and
operations remain intact.

The morning retains the opening strategic showcase and inserts Lab 1 before
Lab 2 without extending the day. A 20-minute Lab 1 is a planning target:
Fireworks deployment may take up to 30 minutes. Pending deployment work must
remain visibly incomplete and be resumed, not hidden by an optimistic checkpoint.

The instrument catalog being authored concurrently is outside this migration
at the owner's request. Its source files are not edited.

## Assumptions and revisit triggers

- Modern browser reading, not live presentation, is the lab interface.
- Revisit when the owner explicitly requests lab presentation views again.
- Upgrade the vendored runtime only on a deliberate version change and
  regression run; do not automatically track the author's local installation.
- Revisit the timebox and deployment mix if a live rehearsal cannot finish
  within the morning allocation or the assigned quota is insufficient.
- Revisit the Lab 1/2 handoff if Lab 2's required models change.

## Validation

Use canonical head synchronization and the 1.2 validator, pytest content and
navigation checks, real-browser desktop/mobile light/dark checks, exact new
accent-pair assertions, copy controls, print targeting, and isolated offline
HTML exports. Record observed outcomes and independent review limits in
`teacher/VALIDATION.md`; local checks cannot certify cloud seat readiness.
