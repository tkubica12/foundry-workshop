# Lab 07 qualification

Source and isolated operator evidence are not room or attendee-role qualification.
Do not advertise the lab as delivery-ready until every live gate is satisfied.
Private identifiers, response bodies, traces and environment receipts stay under
ignored `.workshop\hosted-agent`; no UI screenshots are published.

| Goal Card gate | Evidence and current boundary |
| --- | --- |
| C01: supported integration | Current Responses host; pinned approved-feed resolution; Python 3.13. |
| C02: image and protocol | Actions run [36851584936](https://github.com/tkubica12/foundry-workshop/actions/runs/36851584936) passed actual container readiness, approval/rejection and anonymous GHCR pull. Published Linux/amd64 digest `sha256:3b449eabdc7c56d4f92b491f02ed2cf1a72897a2cda69f8ca9f2a69da0e28dc5`. |
| C03: shared tools and safety | Seven-tool live discovery passed. Two hosted instances completed individually approved reads through both services; answers matched recorded complaint and partner facts. Both rejected chains failed with `interrupt_rejected` and had no executed tool results. Offline forged-resume and write-denial checks pass; no live backend mutation was attempted. |
| C04: telemetry | Actual hosting, graph, model and tool spans, parent links, arguments and results were queried in connected Application Insights and correlated to caller trace IDs. Native Foundry/Azure viewer journey and attendee monitoring permissions remain unqualified. |
| C05: deployment and registry | The same public GHCR digest activated directly in two isolated Hosted Agents in Sweden Central. Both existed concurrently. No ACR was needed or created; no role or shared-resource change was made. |
| C06: lifecycle | Live status and repeated deploy retained one version per seat. New-conversation reset, exact version cleanup, absence verification and repeated cleanup passed. No parent DELETE was issued; a subsequent REST investigation showed the parent can disappear after its last version is deleted. Shared resources and independent monitoring/checkpoint retention are not targeted. |
| C07: learning and reproducibility | Independent educator, safety and source/offline reproducibility rechecks found no material issue. A fresh learner/educator reviewer executed the second prepared operator-seat journey and cleanup without a material blocker. Fresh-machine, attendee-role, native portal and room/timebox qualification remain open. |

Checks on 2026-10-01: 24 isolated Python tests and 152 combined
HTML/content/navigation/export/public-baseline checks passed. The isolated suite
uses an offline model and covers actual Responses HTTP, threaded invocation
serialization, SDK status enums, immutable cleanup and per-turn trace receipts.
Live qualification separately consumed two deployments and 14 Responses POSTs;
all calls were synthetic reads or explicit rejections.

The first deployment exposed the SDK's `AgentVersionStatus` string conversion:
an active enum rendered as its enum name rather than `active`. Polling and
invocation now use its wire value, with regression checks for enum and string
forms. The known version was recovered through status, not another create.
Azure CLI credential acquisition has an explicit 60-second process timeout.

Approval interrupts generate unsuccessful tool spans without remote results;
successful resumed spans carry the actual result. SDK and callback layers can
both record a tool span. Do not count those spans as separate business calls.
The pinned host also logs default `LangChainTracer` callback warnings for
missing interrupt/resume hooks. Actual request, model and tool correlation and
content export passed; the warnings remain visible and are an upstream
compatibility caveat, not suppressed or repaired by patching dependencies.

The public-baseline scan now checks tracked and nonignored candidate source,
not ignored local virtual environments or private `.env` files. MIT export
checks preserve the complete license text while allowing whitespace differences.
All guide navigation and collection export checks passed on the final source.

Canonical guide validation passed 273/273 checks at 1440x900 and 273/273
on its standalone export at 1920x1080: all eight palettes, offline runtime,
reading controls, contrast, print and no-JavaScript fallback. Sibling guide
links require the workshop export collection, whose navigation checks passed.
Visual evidence stays ignored; no PDF or UI screenshot was published.

Final independent safety/operator-source recheck passed all 24 isolated tests
and found no blocking or material issue. It inspected actual correlated results,
parent links and rejection evidence with typed telemetry success values. Enum
normalization, credential timeout and trace history preserve ownership checks,
locks and uncertain-operation markers. A final operator SDK read independently
verified both recorded versions absent after cleanup.

## Independent learner, educator and reproducibility review - 2026-10-01

Reviewed `AGENTS.md`, `AGENDA.md`, the complete Lab 7 HTML guide, `agent.py`
and `system-prompt.txt` with fresh learner context. Followed the guide's
PowerShell workflow using the prepared isolated seat. Substituted
`.workshop\hosted-agent\student-seat\` for the guide's base evidence directory
for `seat.config.json`, `seat.state.json`, `read.json` and `reject.json`;
commands were not byte-identical. Dependencies and authorized operator login
were prepared; no dependency installation, image publication, permission
change or shared-resource mutation was performed.

- Preflight passed. Exactly one hosted version was created and became active
  in 57 seconds. Status and repeated deploy passed; independent SDK enumeration
  found exactly one version with the assigned immutable image digest.
- The approved synthetic complaint journey completed in five Responses POSTs
  (31.0, 29.2, 28.4, 25.1 and 22.9 seconds; 136.6 seconds total).
  Inspected and individually approved the complaint read, two distinct partner
  eligibility searches and the final partner read. One search returned no
  matches; the structured search returned an eligible partner. The final answer
  matched the returned complaint and partner facts.
- Reset into a new conversation passed. Its first read was individually
  rejected: `interrupt_rejected`, failed response and exit code 1, as documented.
  Reset/rejection took 27.0 and 17.5 seconds. Total consumption: one new
  deployment and seven Responses POSTs; no writes to the synthetic services.
- Two bounded read-only queries of the connected telemetry returned 599
  correlated rows across all seven saved turn traces. Hosting requests,
  graph execution, model spans, tool arguments, results and parent links were
  present. Successful complaint and partner reads had
  `gen_ai.tool.call.result`; the final partner result matched the Responses
  output object. Pending approval spans were unsuccessful without results.
  The rejected continuation had no executed tool span. Duplicate SDK/tracer
  spans were not counted as duplicate business calls.
- Observed nine SDK default `LangChainTracer` callback warnings about missing
  `on_interrupt`/`on_resume`. These did not prevent the approval boundary,
  resumed results, final answer, correlation or telemetry export. Not a material
  blocker for this tested path; retain as an upstream compatibility caveat.
  Installed dependencies were not patched and warnings were not suppressed.
- Exact recorded-version cleanup passed in 23.8 seconds. An independent SDK
  read returned `ResourceNotFound`; repeated cleanup reported already cleaned.
  No parent DELETE or shared-resource cleanup was issued. Parent visibility
  was not independently qualified in this SDK run; the later REST observation
  supersedes the earlier assumption that an empty parent remains visible.
  No other seat was altered.

Educator assessment: the optional specialist is a coherent continuation of
Lab 4, distinguishes checkpoint state from managed Memory, and makes execution
ownership and approval evidence concrete. Concise core steps, checkpoints and
recovery paths support the professional-builder audience. No blocking or
material learning, source or tested live-path issue was found.

Qualification limits: this was a prepared operator-seat API rehearsal, not a
new attendee identity or clean machine. Native Foundry/Azure portal navigation,
browser accessibility/visual behavior, attendee-role deployment and monitoring
permissions, facilitator demonstration, room concurrency and the full
45-minute learning timebox remain unverified. Actual command durations do not
qualify reading, discussion or portal-inspection timing. Raw responses,
telemetry, version enumeration and correlation checks remain privately in the
ignored seat directory; no screenshots or private identifiers are published.

## Ephemeral Cloud Shell REST conversion - 2026-10-01

The attendee core now uses Linux PowerShell 7 and Azure CLI `az rest` in
storage-free ephemeral Cloud Shell. Python, its SDK and Docker are not
attendee deployment prerequisites. The agent runtime, immutable image,
production lock and image-publication workflow are unchanged.
Runtime files match the image's recorded source commit
`15c0e9cc8baf0eb2f55b2fcdb30e9e8f6194c620`.

Current local evidence:

- 45 dependency-free REST-client regression assertions passed, including
  uncertain create/turn markers, ownership and digest checks, alternate-state
  seat-lock exclusion, scoped cleanup and repeated absence, exact approvals,
  typed NotFound handling, authentication-independent backup, native executable
  selection and subprocess timeout.
- All 24 isolated agent Python tests and 252 related HTML/content/navigation/
  export/public-baseline/browser checks passed. A hidden empty recovery anchor
  found by the browser checks was replaced with the visible section heading.
- Canonical guide validation passed 300/300 checks at 1440x900; the
  standalone guide passed 300/300 at 1920x1080, including offline runtime,
  light/dark themes, reduced motion, print and no-JavaScript fallback.
  Standalone sibling links require the workshop collection.
- Independent Educator and destructive-safety reviews identified two material
  source issues: locking by state filename and an unexplained image/source
  boundary. Directory-wide locking and explicit operator source-commit
  qualification resolved them. The scoped recheck found no blocking or
  material issue. The final safety evidence review inspected actual hashes,
  archive receipts and typed telemetry results without a remaining material
  finding.

Maintained-client live evidence consumed exactly two additional isolated
deployments and ten Responses POSTs in the approved existing project. Neither
deployment changed roles, shared resources, models, image publication or
synthetic backend data.

- Both seats passed actual CLI preflight, activation, status and repeated
  deploy without another version POST. Each approved chain used three
  Responses POSTs: an individual complaint read, an individual partner read
  and the returned factual answer. Each separate rejection used two POSTs
  and persisted `failed / interrupt_rejected`, with the expected client
  failure exit and no executed tool result.
- The first seat returned 398 correlated telemetry rows over five turns.
  The independent Student live-path reviewer inspected 403 rows for the
  second seat: hosting, graph, model, arguments/results, resolved parent
  links and saved previous-response relationships. Duplicate instrumentation
  spans represented two business reads, not four executions. Actual returned
  complaint/partner facts matched the answers; rejected continuations had no
  executed tool result.
- Both seats created private recovery ZIPs, restored their trusted archive
  into an empty seat directory, resumed the recorded active version, deleted
  only that version, independently verified absence and repeated cleanup
  without another DELETE. Final exported archives contain four matching JSON
  receipts, no process locks or credential fields, and cleaned state.
  Recorded remote client hashes match the maintained repository scripts.
- Owned Cloud Shell console absence was independently verified after the
  rehearsals. The approved ephemeral profile remains; no storage account was
  created. File loss and agent cleanup are separate lifecycle boundaries.

Real Cloud Shell testing exposed multiple `az` executable matches and the
service's structured `not_found` error code. Both were corrected in the
maintained client with regressions; authorization failures remain failures.
Private terminal transport exceeded the Linux argument limit when sending a
large prepared snapshot, and a later review terminal disconnected before
setup. Neither attempt deployed a version or sent a Responses POST. The
transport was changed to bounded script-file chunks, and the remaining
independent review completed from an empty isolated checkout. These transport
helpers are private test infrastructure, not attendee prerequisites.

The independent Student/source review and the resumed live-path review found
no blocking or material issue in the exercised core. The live rehearsals used
prepared authorized operator credentials and an in-memory first-party terminal
token bridge. Unpublished maintained scripts were transferred as a prepared
source overlay; the runtime source came from the public checkout. Archive
bytes were exported through the test transport, not the browser toolbar.
Do not equate these tests with browser-only first login, device-code recovery,
native upload/download controls, Foundry/Azure portal trace viewers, intended
attendee permissions, room concurrency or the complete 45-minute learning
timebox. Those delivery gates remain open.
