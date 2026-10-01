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
| 15:15-15:40 | 6. Add managed memory | [Lab 6](docs/guides/chapter-6-managed-memory.html): 20-minute core plus recovery and discussion. Compare no-memory chats with stored profiles and summaries; use the same identity and isolated per-run resources. |
| 15:40-16:15 | Connect it: code-first and channel architecture | Connect prompt agents, managed Memory, hosted code and channel publication. The full optional Lab 7 is a separate 45-minute extension, not squeezed into this discussion. |
| 16:15-17:00 | Closing: operating and adopting agents | Architecture synthesis and planned Autopilot demonstration; qualify separately. |

Lab 6 is the last mandatory lab. [Lab 7](docs/guides/chapter-7-hosted-agent.html)
is an optional 45-minute code-first LangGraph Hosted Agent extension using the
same MCP tools and correlated traces. Lab 8 is planned as optional publication
of an existing agent to Teams through Publish; it is not published yet.
Neither optional lab is a prerequisite for completing the core day.
Put the broad platform message in the opening showcase; use the labs for depth.
Use demonstrations for breadth and one meaningful outcome per lab. Keep optional
extensions outside the core timebox. A published guide does not certify a live
environment. Lab 4 has a guide and live API qualification; its portal path
still needs attendee-identity rehearsal. Lab 5 has isolated live API and portal
evidence; attendee permissions, room concurrency and timing remain separate
qualification gates. Lab 6 has an isolated native portal rehearsal; attendee-role
access, room concurrency and its timebox remain separate qualification gates.
Lab 7's qualification is tracked separately in
[its operational evidence](student/labs/hosted-agent/VALIDATION.md).

Lab 1 uses Sweden Central and per-seat deployments: one primary GPT model at
100,000 TPM, plus Luna and GLM Flash at 50,000 TPM each. Confirm Lab 2's separate
guardrail and telemetry permissions before transitioning; connect Application
Insights in each seat's own Lab 1 project at the start of Lab 2. Reuse the primary Sol
and a ready Luna or GLM deployment where compatible. Model IDs in later labs
are examples: an existing alternative is valid when capacity differs and the
required agent, evaluator or tool capability is confirmed. Keep agent and judge
deployments fixed within each baseline/candidate comparison. Lab 1 does not
qualify those capabilities. The Lab 1 timebox is a target, not a deployment
latency guarantee; Fireworks can take up to 30 minutes.

[Open the labs](docs/index.html) · [Delivery roadmap](PLAN.md)
