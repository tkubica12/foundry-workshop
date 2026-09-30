# 0001. Keep the build lab focused on model choice and guardrails

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Workshop content owner
- **Relates to:** [0006](0006-customer-neutral-public-baseline.md)

## Context

The first hands-on lab must fit a thirty-minute core path in a one-day workshop.
Hosted provisioning and persistent memory add configuration, latency and access
boundaries that distract from the first useful agent outcome. The teacher can
demonstrate those capabilities without requiring every attendee to deploy them.

This public record preserves the scope decision without transferring historical
environment measurements or preview-service limitations to a new deployment.

## Decision drivers

- One meaningful outcome with recovery margin.
- No infrastructure provisioning inside the first lab.
- Observable differences from model choice and an explicit safety control.
- Fictional inputs suitable for a general professional-builder audience.
- A progressive agent journey that continues into evaluation.

## Options considered

### Option A - Repeat the complete hosted-agent demonstration

High breadth, but provisioning and runtime setup dominate the timebox.

### Option B - Build a prompt agent, compare replies and inspect a guardrail

Use prepared models and portal access. Compare a small number of replies, then
test an input control with a synthetic email and a benign negative control.
This is the chosen option.

### Option C - Teach persistent memory in the first lab

Interesting, but requires separate model, storage and isolation qualification.
Keep it outside this core path.

## Decision

Choose Option B. Use the fictional pickup assistant in
`docs/guides/chapter-2-build-agent.html`. Compare prepared models from two vendors,
then use the prepared local model route for the control experiment.

Distinguish a policy block, model refusal and platform failure. Inspect the
actual trace rather than inferring enforcement from a configured policy name.
Keep the agent and its original instructions for the evaluation lab.

The retained stock-scoring harness is optional teacher material, not the active
attendee path. Neither one fluent reply nor one successful block establishes
production quality or general personal-data detection.

## Consequences

The first lab needs only prepared portal access. The facilitator still qualifies
model availability, guardrail support, permissions and trace access in advance.
Hosting and memory remain separately qualified demonstrations or later work.

## Assumptions and revisit triggers

- Prepared portal access is more reliable than attendee-local runtime setup.
- Revisit if an attendee identity cannot perform a documented step.
- Requalify preview controls and model routes before every delivery.
- Reduce scope or move optional depth if rehearsal exceeds thirty minutes.

## Validation

The content tests check prompts, the selective-control sequence and retained
instructions. Browser tests cover reading, copying, navigation and media.
These are local checks; actual attendee sign-in, control attribution and lab
timing require a separate live rehearsal in the delivery environment.
