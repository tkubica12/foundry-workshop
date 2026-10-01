# Lab 04 qualification

Execution dates: **2026-09-30 and 2026-10-01**. Scope: source, direct MCP,
isolated Foundry API tests and the operator's signed-in Edge portal.
**Attendee-role access and room delivery remain separately unqualified.**

## Observed

- Clean local HTTP processes passed the lab's exact seed read, eligible-partner
  lookup, generated-case creation, assignment, note, independent readback,
  stale-version rejection and exact generated-record deletion.
- The same direct MCP write journey passed against both deployed backends.
  No seeded complaints or partners were modified. One initial remote session
  disconnected during initialization; the subsequent fresh journey passed.
- Three owned project connections and a curated two-server toolbox were created
  through the live Foundry/ARM APIs. A separate clean per-seat preparation
  through `prepare_toolbox.py` passed; repeating it reused the same toolbox
  version and connections.
- The isolated prompt agent discovered the filtered toolbox, requested platform
  approval, called partner search, created its own marked complaint and read it
  back. Actual discovered names include the `partners___` / `complaints___`
  prefixes. The endpoint accepts `agent_reference`; a documented older `agent`
  request property was rejected as deprecated.
- After a no-write partner proposal, the agent refreshed complaint/partner facts,
  requested approval for the exact assignment at version 1, assigned the partner
  and read back version 2 with the expected owner, partner and unchanged status.
  Real provider rate limits interrupted approval continuations. Record inspection
  confirmed no assignment before resuming the pending approval; the write was not
  blindly replayed.
- The connected Application Insights resource returned actual ingested telemetry
  for the isolated agent, including toolbox `tools/list` and business
  `tools/call` spans. The assignment's toolbox span and agent `execute_tool`
  dependency share a trace ID; metadata contains the exact approved arguments,
  response ID, toolbox version and returned version-2 record.
  Response bodies, exact IDs, independent backend readbacks
  and telemetry query output are held in ignored private evidence, not public
  fixtures or screenshots.
- Canonical HTML validation passed **269/269 checks** at both 1280x720 and
  1920x1080: all eight palettes, contrast, offline/reduced-motion reading,
  no-JavaScript content and reading print output. The final added metadata reveal
  passed **278/278 checks** at 1280x720. No Slides or Sheet view exists.
- Targeted source, browser, navigation and reading regressions passed **143 tests**.
  The navigation publication inventory assertion is separately blocked by a
  concurrently created, unlinked Lab 5 HTML file outside this change's scope;
  that assertion is not counted as passed.
- The optional note passed in local/deployed direct MCP rehearsal, but not through
  the live agent: rate-window waits and inactivity were followed by the generated
  case disappearing from volatile storage. No successful live note or live
  approval-denial outcome is claimed. This is a concrete delivery reliability
  limit, not merely a theoretical warning.

## Release gates

Rehearse the published guide with the intended attendee identity and target
portal rollout before delivery. Verify the actual tool selector, identity
connection, approval controls, response-to-trace links, trajectory inputs/outputs
and exact call correlation. A connected monitoring resource or ingested API
telemetry is not proof that the attendee can inspect those fields in the portal.

Measure the 55-minute core and verify rate-window capacity for the room. Every-call
approval is intentional but accumulates model context; optional note/denial work
must not consume core trace time. An API-only run is not a Student tester's
completed browser journey.

## Independent reviews

### Concise guides, 2026-10-01

The MCP and knowledge guides were shortened by about half, preserving canonical
reading controls, stable anchors, exact copyable inputs and safety checkpoints.
Both share explicit previous/next navigation. The final source/navigation/browser
suite passed 138 tests; canonical offline/no-JavaScript/print validation passed
278 checks for Lab 4 and 308 for Lab 5 at 1280x720 in all eight palettes.

Independent Educator/local Student and safety reviews inspected the actual
reductions and found no blocking/material issues. The Educator also passed 33
focused checks. A narrow follow-up approved the distinction between conversational
write confirmation and runtime approval cards for read calls.

### Observed Edge controls

Actual portal registration, toolbox creation/publishing, seven-tool curation,
Microsoft Entra / Agent Identity attachment, individual Approve once choices,
both-server reads and conversation tool input/output/metadata were exercised.
Connection names are limited to 27 characters in the tested UI. Toolbox-to-agent
attachment uses its MCP endpoint, not an observed native one-click shortcut.

The first portal create succeeded after recovery from ERR_NETWORK. The generated
case subsequently disappeared during prolonged inactivity; no seed record was
used as a substitute.

On 2026-10-01 the refreshed Edge completed the concise create, proposal and
assignment prompts through real portal controls and individual Approve once
cards. The new case was unassigned at version 1; the verified eligible partner
was assigned and read back at version 2 with unchanged status `new`. An
independent direct MCP read confirmed the same marker, ID, version and partner.
No seed/partner record was changed.

The actual portal conversation viewer then opened the assignment's
`execute_tool` span and Metadata tab. Its approved complaint/partner IDs,
`expected_version`, response/trace identifiers and `gen_ai.tool.call.result`
matched the version-2 readback. A corresponding inner `tools/call` span was
visible separately. Screenshots and raw metadata remain in private evidence;
the generated case was subsequently deleted by exact ID/current version, and
its marker search confirmed absence.

The existing GPT-5.2 deployment hit token-rate limits during rehearsal. Only
the isolated test agent was switched to an existing GPT-5.6 deployment; no
deployment, quota, role or backend scaling was created or increased. This is
not evidence that the room's prepared model has enough aggregate capacity.

### Earlier qualification

- Educator and fresh-context Student review inspected the guide and inputs and
  exercised the actual local reading UI. Ten Lab 4 tests passed; no blocking or
  material artifact finding. The Student portal journey remains unexecuted.
- Clean-room reproducibility/safety review ran the documented clean local HTTP
  write journey and inspected preparation, credentials, ownership, failures and
  exact deletion. It found repeat preparation accepted a connection whose
  `isSharedToAll` setting had drifted to true.
- The guard now rejects sharing drift alongside target/auth/audience drift.
  Independent narrow re-review passed the regression and additional missing-field
  checks, with no blocking/material residual issue. The 429 recovery and optional
  span-metadata guidance also passed that narrow educator review.

## Temporary-resource cleanup

The qualification agent, both temporary toolboxes and their six temporary
connections were removed only after checking each resource's exact recorded
scope and live ownership metadata. All nine subsequently returned 404.
The generated qualification case was already absent; no backend deletion was
performed for it. Direct verifier cases were explicitly deleted by their own
exact-ID cleanup. The original project, models, Application Insights and both
MCP applications remain unchanged. Private receipts and telemetry evidence remain
available for audit.

The separate browser-rehearsal configuration (one operator-owned test agent,
one toolbox and three project connections) is retained for operator inspection.
Its exact names are in private session receipts, not attendee source. Remove
only that scope when it is no longer needed; the final generated complaint was
already cleaned up. Shared infrastructure and role/scaling settings are unchanged.

## Evidence manifest

Required coverage was official product documentation plus local implementation
and observed runtime behavior. No internal workplace or community claims are
used. Publication/update dates were not supplied by the retrieved pages; the
consultation and execution date is 2026-09-30.

| Source / lookup | Tool and status | Evidence use |
| --- | --- | --- |
| [Toolbox](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/toolbox) | Microsoft docs fetch; 1 page | Curation, endpoint/version contract, runtime approvals |
| [MCP](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/model-context-protocol) | Microsoft docs fetch; 1 page | Connection, allowlist, approval and prompt-agent patterns; deprecated request property corrected using observed runtime rejection |
| [Tracing](https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-setup) | Microsoft docs fetch; 1 page | Server-side enablement, access, correlation, privacy |
| [ARM connections 2026-07-01](https://learn.microsoft.com/azure/templates/microsoft.cognitiveservices/2026-07-01/accounts/projects/connections) | Microsoft docs fetch; 1 page | ARM connection structure; caller-token discriminator verified live rather than inferred from incomplete schema |
| [ARM connections 2025-06-01](https://learn.microsoft.com/azure/templates/microsoft.cognitiveservices/2025-06-01/accounts/projects/connections) | Microsoft docs fetch; 1 page | Consulted earlier schema; not the selected deploy API |
| [PromptAgentDefinition](https://learn.microsoft.com/javascript/api/@azure/ai-projects/promptagentdefinition?view=azure-node-preview) | Microsoft docs fetch; 1 page | Agent configuration structure |
| MCP/toolbox registration; tracing; custom-key connections; agent REST; prompt/toolbox definitions | Microsoft docs search; 5 completed searches, 10 results each | Discovery; registration uses [first-party server guidance](https://learn.microsoft.com/azure/foundry/mcp/build-your-own-mcp-server) |
| Foundry connection samples; Application Insights KQL samples | Microsoft code-sample search; 2 completed searches, 10 results each | Consulted code patterns; KQL used to inspect actual telemetry |
| Attempted REST agents/create-version reference | Microsoft docs fetch; blocked by unavailable page, 0 pages | Not used as evidence |
| Existing MCP models, fixtures, verifier and operator contract | Local file reads; searched | Exact tool schemas, synthetic data, lifecycle and storage behavior |
| Clean local / deployed MCP; own Foundry resources; own telemetry | Python, Azure CLI and authorized HTTP; executed | Scope and outcomes listed above; private receipts and raw results retained |
| Attendee portal journey | Browser page inspected; sign-in/testing explicitly deferred | Not qualified; no click-path or attendee-role success claim |

The complete consulted-search URL ledger is retained with private session
evidence. Search-result counts include duplicate SDK language pivots and do not
represent independent sources.
