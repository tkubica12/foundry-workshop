# 0007. Focus the repository on published labs

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Workshop owner

## Context

The repository publishes only Labs 2 and 3. It also contained an unqualified
hosted-agent teacher demo, a fixture pack for an unpublished stock-operations
exercise, an optional worksheet for that fixture, and legacy presentation assets.
Those branches added dependencies and tests without supporting either published
lab.

## Decision drivers

- Keep every committed runtime and test tied to a published attendee journey.
- Reduce dependency, maintenance and qualification scope.
- Avoid implying that planned afternoon material is delivery-ready.
- Preserve reusable authoring templates and validation of the published HTML.

## Options considered

### Option A - Keep future material beside the published labs

This preserves prototypes, but makes the repository look more complete than the
qualified attendee experience and requires unrelated dependencies and tests.

### Option B - Remove material without a published journey

This keeps the repository small and makes its validation boundary explicit.
Future labs can add their own source, automation and tests when their guide is
implemented.

## Decision

Choose Option B. Remove the hosted-agent demo and its lifecycle tests, the
stock-operations fixture and its contract tests, the optional learning passport,
and legacy assets not referenced by published pages or authoring templates.
Retain Lab 2 and Lab 3 inputs, attendee HTML, shared HTML runtime, authoring
templates and tests that validate those surfaces.

This decision supersedes the teacher-harness retention in ADR 0002 and the
teacher contract in ADR 0003. It does not reject those designs; their
implementation no longer belongs in the published-labs baseline.

## Consequences

The project no longer needs Azure or LangChain Python packages. Local validation
uses only pytest, Playwright and Node.js. Planned demos and labs must return as
self-contained, qualified deliverables rather than dormant source.

## Assumptions and revisit triggers

- Labs 2 and 3 remain the only published attendee journeys.
- Revisit when a future lab has an attendee guide, prepared environment and
  relevant review evidence ready to land together.
- Reintroduce deployment dependencies only with the automation that uses them.

## Validation

Run the complete pytest suite, the standalone HTML export checks and
`git diff --check`. Confirm every remaining tracked asset is referenced by a
published page, retained authoring template, validation command or repository
instruction.
