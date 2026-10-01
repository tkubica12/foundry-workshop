# Lab 04 operator contract

[Attendee HTML guide](../../../docs/guides/chapter-4-connect-tools.html) ·
[Qualification evidence](VALIDATION.md)

55-minute core inside the 75-minute tools chapter: preflight 5, curation/connection 15,
read/create 10, assignment 10, observability 15 minutes. Demonstrate the outcome
before hands-on; reserve the remaining chapter time for architecture and recovery.
Note creation and approval denial are optional extensions.

## Starting state

Use the existing [MCP services](../mcp-services/README.md), their frozen
FastMCP environment, ignored `.env` and `.deployment.json`. No new packages,
backend deployments or infrastructure are required. Operator platform: Windows,
Python 3.13, the existing MCP virtualenv, Azure CLI signed in to the explicitly
authorized tenant/subscription. Azure calls can incur existing inference and
telemetry charges. Obtain project-change authorization first.

Pre-provision per-seat:

- the Lab 3 agent and an MCP-capable model deployment;
- two `RemoteTool` server connections with a secret `Authorization` header;
- authoring access for a per-seat toolbox with exactly the seven guide tools;
- Foundry project access for the agent identity used by the browser's
  `Microsoft Entra / Agent Identity` toolbox connection, audience
  `https://ai.azure.com`;
- enforced approvals on both inner servers and outer agent attachment;
- Application Insights connection and attendee telemetry read permissions.

The operator/developer and applicable runtime identity need Foundry User project
access. Caller passthrough needs the caller's access; it does not bypass runtime
identity requirements. Grant no new roles through these scripts. Check the
intended attendee, not just an administrator. Telemetry queries need the documented
Log Analytics Reader access; protected tables may require additional reader access.
See the authoritative [tracing prerequisites](https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-setup).

## Prepare a fallback seat

From the repository root, set `$projectEndpoint` and `$projectResourceId` to
the explicitly approved project's endpoint and exact ARM ID. These are private
operator inputs, not source defaults. Confirm the selected Azure account first.
Use the same seat and state path for retries:

```powershell
az account show --query "{tenant:tenantId,subscription:id}" -o json
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\connect-tools\scripts\prepare_toolbox.py --project-endpoint $projectEndpoint --project-resource-id $projectResourceId --seat S07 --state .workshop\connect-tools\seat-S07.json --confirm
```

The core browser path starts from registered server connections, creates and
publishes the seat's own toolbox, and attaches its MCP endpoint to the agent.
The script below is the full prepared-toolbox recovery path, not an SDK
prerequisite for that browser path. It retains the previously qualified
caller-token `UserEntraToken` connection; add this prepared connection from
**Configured** rather than trying to select a caller-token option in the portal's
Entra Type dropdown, which exposes Agent Identity and Project Managed Identity.

This creates only `lab04-s07-partners`, `lab04-s07-complaints`,
`lab04-s07-toolbox` and `lab04-s07-tools` inside that project. It does not change
agents, role assignments, models, monitoring, infrastructure or backend records.
Secrets are read in memory from `MCP_API_KEY` or the backend's ignored `.env`;
no secret command-line argument is used. The private receipt contains scope,
names, version and endpoint, never credentials. Do not share it publicly.

Repeat execution checks ownership and configuration and reuses the same toolbox
version. A mismatch fails instead of changing an existing resource or promoting
a default. Run one preparation for a seat at a time. After any failure, inspect
the named resources and private receipt; a `preparing` status means partial
configuration can remain. Correct the failure and repeat with exactly the same
scope. No mutation is automatically retried. ARM/API requests are bounded to
90 seconds, Azure token acquisition to 60 seconds; provider correlation IDs are
reported for HTTP failures. A secret rotation is a separate authorized update,
not a side effect of rerunning this script.

Hand out the assigned tenant/subscription/project, agent/model, seat and two server
connection names. Supply a prepared toolbox/version/consumer connection only for
the fallback path. Do not hand out the broad backend key. Demonstrate registration
using **Connect a tool / Custom / Model Context Protocol (MCP) / Create**;
connection names are limited to 27 characters by the tested portal.

The observed student path is **Tools / Toolboxes / Create toolbox**, **Included /
Add / Add tool / Configured**, per-server comma-separated **Allowed tools** and
**Never auto-approve tools**, then **Publish** and **Call this toolbox / Copy
endpoint**. Agent attachment uses **Tools / Add / Add tools / Custom / MCP /
Create**, the toolbox endpoint and **Microsoft Entra / Agent Identity**. There is
no tested native one-click toolbox-to-agent shortcut. Preserve **Never
auto-approve tools** on the outer attachment too.

## Rehearse and release

```powershell
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\connect-tools\scripts\verify_journey.py --local --confirm
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\connect-tools\scripts\verify_journey.py
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\connect-tools\scripts\verify_journey.py --confirm
python -m pytest tests\test_chapter_4_content.py tests\test_docs_html.py tests\test_workshop_navigation.py
```

The default remote verifier is read-only. `--confirm` authorizes one generated
synthetic complaint: create, assign an eligible partner, append a note, verify
readbacks and reject a stale version, then delete only that exact owned ID using
its current version. It never edits seed cases or partners. It reports the unique
marker and generated ID before subsequent writes. If creation has an uncertain
outcome, search that marker before retrying. If exact cleanup fails, those printed
identifiers locate the retained record. No mutation is retried automatically.
Local mode starts two clean loopback processes with a random key and stops only
those child processes.

These checks verify **direct MCP**, not Foundry or portal behavior. Separately run
the actual guide with the intended attendee identity: attachment, exact prompts,
every approval, assignment/readback, optional note/denial and the exact trace.
Keep private response/trace IDs, screenshots and timings in ignored evidence.
Do not release a seat based on health, tool discovery or mocks alone.

Use **Approve / Approve once** for each inspected call, never **Always approve
this tool** or **Always approve all tools**. Inspect search results through the
reply's **Traces / Trajectories / execute_tool / Input + Output** before the
create approval if the pending card displays only arguments.

Control token consumption: each approval continuation carries conversation/tool
context. A 429 is not permission to bypass approval. Wait for the deployment's
rate window, inspect record state, and continue the pending approval only after
confirming the action has not already occurred. Never resend the entire write
prompt as a generic rate-limit retry.

Qualification observed loss of the generated case after extended inactivity.
Before releasing the room, qualify the actual continuous journey and backend
lifetime, including pauses for approval and tracing. If class pacing or rate-window
waits cause state loss, stop release and obtain authorization for stable running
capacity or isolated durable backends; the scripts do not change scaling settings.
Keep note/denial extensions out of the core path until this limit is resolved.

## Cleanup and reset

The learner toolbox deliberately excludes deletion. For each reported generated
case, retrieve it with an operator MCP client, compare the exact marker and ID
with the seat's notes, and delete only that record with its current version.
If ownership cannot be proven, retain it for investigation. Do not delete seeded
complaints or partners and do not reset the shared backend during class.

For Foundry configuration cleanup, inspect the private receipt and live
`lab04_owner` metadata first. Detach the toolbox from the seat's agent in a new
version. Remove only the named owned toolbox and its three connections after
confirming no other consumer uses them. Retain the project, agent history,
monitoring, model deployments and shared MCP services. Telemetry remains subject
to configured retention. Backend cloud teardown is separately authorized and
uses the existing MCP operator contract.

Preparation failure leaves an actionable receipt; no broad cleanup or automatic
role changes are attempted. Missing portal features or traces block release:
retain API evidence and schedule the explicit attendee-identity rehearsal.
