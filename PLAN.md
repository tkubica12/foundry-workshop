# One-day workshop roadmap

The active publication is [lab navigation](docs/index.html): Lab 1 creates a
Foundry project and deploys models; Lab 2 builds the agent; Lab 3 evaluates and
improves it; Lab 4 connects a curated MCP toolbox and inspects a scoped action;
Lab 5 connects knowledge and compares a balanced core against fixed references.
Lab 6 adds managed memory and distinguishes profiles from conversation summaries.
Labs are HTML reading guides, without slides or one-pagers.
Next: qualify Lab 4's portal journey and Lab 5's attendee access/concurrency,
and Lab 6's attendee roles/concurrency. The LangGraph hosted specialist is now
an optional Lab 7 with a code-first LangGraph implementation, prepared image and
explicit read approvals. Lab 6 remains the last mandatory lab. Lab 8, publication
of an existing agent to Teams through Publish, is optional and not published.
Keep the complete builder journey inside the single day in [AGENDA.md](AGENDA.md).
Use a polished opening showcase, optional Teams integration and a closing
Autopilot demonstration for breadth. Qualify each live path separately before
delivery; no external demo repository or private handoff is a prerequisite for
continuing development here.

## Implementation order

1. Qualify project creation, the three model deployments and playground replies,
   then the published build and evaluation paths under an actual attendee identity.
   Preflight the shared quota, per-seat permissions and Fireworks enablement.
   Confirm Lab 2's separate model and control prerequisites rather than treating
   Lab 1 deployments as replacements.
2. Rehearse the published tools lab with an attendee identity, portal attachment,
   enforced approvals and exact traces. API and backend checks are not a portal
   qualification; see the [Lab 4 evidence](student/labs/connect-tools/VALIDATION.md).
3. Qualify the published knowledge lab at room concurrency and with attendee roles.
   Keep 20 balanced cases in the core and all 100 as a separately timed extension.
4. Rehearse managed memory under attendee identities and at room concurrency.
   Rehearse optional Lab 7's attendee access and native trace-viewer journey;
   its image, hosted calls, correlated telemetry and lifecycle have operator
   evidence. Keep its full core outside the mandatory day.
5. Qualify the opening and closing demonstrations, then rehearse the complete day.

Keep published examples fictional and customer-neutral. Do not add real customer
data, named organizations, production endpoints or copied operational evidence.

- [Public sequence](AGENDA.md)
- [Publication decision](docs/adr/0005-labs-first-publication.md)
- [Public baseline decision](docs/adr/0006-customer-neutral-public-baseline.md)
- [Validation and delivery boundaries](teacher/VALIDATION.md)
