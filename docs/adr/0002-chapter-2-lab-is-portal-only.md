# 0002. Keep the build lab portal-only and the scored harness teacher-only

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Workshop content owner
- **Relates to:** [0001](0001-chapter-2-student-lab-scope.md),
  [0006](0006-customer-neutral-public-baseline.md)

## Context

The build lab has a thirty-minute hands-on timebox. Installing Python, SDKs and
credentials on unknown attendee machines would consume its recovery margin.
The portal provides a visible agent conversation, safety-control attribution
and trace inspection without a local installation step.

Historical operator access does not establish attendee access. Qualify the
documented portal journey under the intended identity for each delivery.

## Decision drivers

- Avoid attendee installation and shell failures.
- Keep model judgement with the reader, rather than hiding it behind a score.
- Preserve repeatable scoring as an optional teacher demonstration.
- Require no external private repository or machine image.

## Options considered

### Option A - Run the harness on attendee laptops

Provides repeatable statistics, but adds runtime and authentication setup.

### Option B - Preinstall the harness on per-seat machines

Possible in a separately prepared environment, but adds machine access and
maintenance to a lab that does not need them.

### Option C - Use the portal for the core lab

Chosen. Compare replies by eye, inspect the actual control result, and carry
the agent forward into a more deliberate evaluation.

## Decision

Choose Option C. The published build guide contains no shell or installation
step. Retain `teacher/demos/build-host-agent/harness/` for an optional teacher
segment and document its separate contract, state journal and cleanup scope.

State the limitation clearly: the first comparison is a smoke test, not a
production evaluation or a guarantee that one model always outperforms another.
Do not promise that a particular model fails in front of every attendee.

## Consequences

Prepared portal sign-in is the critical path. The facilitator must verify
model selection, policy creation and assignment, saved versions and trace
visibility at attendee privilege. Teacher-only trial statistics can add depth
without making attendee completion depend on a runtime.

## Assumptions and revisit triggers

- Revisit if portal controls or trace visibility are unavailable to attendees.
- Requalify model routes and safety controls when their configuration changes.
- Revisit the harness boundary only if a prepared runtime demonstrably improves
  learning without consuming the timebox.
- Treat live-service differences as observations to verify, not permanent rules.

## Validation

Local checks exercise guide structure, synthetic prompts, copy controls and
media. The guarded harness tests cover mocked scoring and cleanup boundaries.
No local result certifies current portal permissions or live workshop timing.
