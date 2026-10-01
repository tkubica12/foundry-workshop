# One-day workshop

Build one agent progressively. Use **See it → Work with it → Connect it**:
watch the outcome, make one meaningful change, then discuss architecture and
operating responsibilities. Confirm access and pre-provision slow setup before
hands-on work. Use synthetic data throughout.

## Target timetable

Plan for 09:00-17:00, including two breaks and lunch. The allocations below are
design targets, not measured completion times. Rehearse the complete day with
the intended attendee identity before advertising it as ready to deliver.

| Time | Focus | Delivery |
| --- | --- | --- |
| 09:00-09:20 | Opening showcase: the complete agent experience | Planned opening teacher demonstration; establish the broad platform value before the first break. |
| 09:20-09:45 | 1. Create a project and deploy models | [Lab 1](docs/guides/chapter-1-foundry-setup.html): 20-minute browser path, then connect identity, resource, project and deployment. Preflight access, quota and Fireworks enablement before the day; carry pending deployments forward without treating them as complete. |
| 09:45-10:30 | 2. Build an agent | [Lab 2](docs/guides/chapter-2-build-agent.html): 30-minute core path, with demonstration, architecture discussion and recovery margin. |
| 10:30-10:45 | Break | |
| 10:45-12:00 | 3. Evaluate and improve | [Lab 3](docs/guides/chapter-3-evaluate-agent.html): about 55 minutes for the guided path; retain discussion and recovery time. |
| 12:00-12:45 | Lunch | |
| 12:45-14:00 | 4. Connect tools | [Lab 4](docs/guides/chapter-4-connect-tools.html): 55-minute core with browser-authored toolbox curation from prepared MCP connections, a scoped assignment and 15 minutes of trace inspection. Reserve the rest for demonstration, discussion and recovery. Qualify attendee permissions and room pacing before delivery. |
| 14:00-15:00 | 5. Ground with knowledge | [Lab 5](docs/guides/chapter-5-knowledge-base.html): 45-minute core with a balanced 20-case before/after comparison over 20 synthetic PDFs. Reserve 15 minutes for recovery and architecture. Keep the full 100-case run as a separately timed extension; preflight model/judge throughput and Search capacity. |
| 15:00-15:15 | Break | |
| 15:15-16:15 | 6. Add a hosted specialist with LangGraph | Planned lab; not published. |
| 16:15-17:00 | Closing: operating and adopting agents | Architecture synthesis and planned Autopilot demonstration; qualify separately. |

Teams integration is optional, not a prerequisite or promised hands-on outcome.
Put the broad platform message in the opening showcase; use the labs for depth.
Use demonstrations for breadth and one meaningful outcome per lab. Keep optional
extensions outside the core timebox. A published guide does not certify a live
environment. Lab 4 has a guide and live API qualification; its portal path
still needs attendee-identity rehearsal. Lab 5 has isolated live API and portal
evidence; attendee permissions, room concurrency and timing remain separate
qualification gates. Lab 6 is not published.

Lab 1 uses Sweden Central and per-seat deployments: one primary GPT model at
100,000 TPM, plus Luna and GLM Flash at 50,000 TPM each. Confirm Lab 2's separate
model, guardrail and trace prerequisites before transitioning; Lab 1 does not
provision those capabilities. The Lab 1 timebox is a target, not a deployment
latency guarantee; Fireworks can take up to 30 minutes.

[Open the labs](docs/index.html) · [Delivery roadmap](PLAN.md)
