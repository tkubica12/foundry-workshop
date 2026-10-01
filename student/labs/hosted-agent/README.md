# Optional Lab 07: code-first Hosted Agent

Attendee path: [HTML guide](../../../docs/guides/chapter-7-hosted-agent.html).
Use ephemeral Azure Cloud Shell **PowerShell**, Git and Azure CLI `az rest`.
No local Python, SDK, uv or Docker installation is required. Python runs in
the published Linux/amd64 image. The graph discovers the seven Lab 4 tools,
requires individual read approvals and rejects all writes before MCP execution.

## Operator preparation

Pre-register `Microsoft.CloudShell`; qualify the intended attendee account,
Foundry Project Manager access, Hosted Agent capacity, agent runtime model/tool
permissions and monitoring read access. Prepare the existing model, Lab 4
version-pinned toolbox and connected Application Insights. Do not repair denied
calls with broad subscription roles.

Run **Publish workshop Hosted Agent** on an authorized commit. The workflow
tests the actual Responses host, publishes to public GHCR, verifies anonymous
pulling and records the immutable digest in `hosted-agent-image`. A new package
may need **Package settings > Change visibility > Public**. An anonymous pull
failure is not permission to put registry credentials in an image.

Retain the workflow's source commit alongside its digest. Before distributing
the workshop checkout, verify `agent.py`, `system-prompt.txt`, Dockerfile and
production lock match that image-source commit; a delivery-client-only update
need not rebuild the image. Stop preparation if the runtime differs.

Fill `config.example.json` from the authorized assignment and digest receipt.
Supply a separate private `seat.config.json` for each unique
`lab07-<run>-sNN` name. Distribute it privately, not in the public checkout.
Toolbox mode uses refreshed Entra authentication. Direct MCP mode is an
operator alternative using a Foundry connection placeholder, never a literal
key. Enable content capture only for approved synthetic data.

The HTML guide is the command reference. `scripts/lab07.ps1` covers preflight,
deploy, status, recover-create, start, approve, reject, cleanup and backup.
`scripts/rest-common.ps1` validates configuration and ownership, bounds Azure
CLI processes, locks all seat operations and records uncertain POSTs. Supported
client platform: Linux PowerShell 7 in Azure Cloud Shell; not Windows `az.cmd`.
It uses API `v1` and Responses protocol `2.0.0` without preview headers.

## Recovery and destructive scope

Private config/state/conversations share one seat directory under ignored
`.workshop/hosted-agent/`. REST and Python operator receipts use different
fingerprint formats; do not mix clients on one seat. Export JSON receipts with
`backup` and download the printed ZIP with **Manage files > Download** after
deployment, conversation turns and cleanup. A ZIP left in ephemeral Cloud
Shell is not a backup. Restore your own newest trusted archive into an empty
seat directory; never overwrite newer state.

- Known-version timeout: run `status`, never create another version.
- Uncertain create: preserve intent; `recover-create` accepts exactly one
  matching owned version without a POST. No unique match means manual review.
- Uncertain turn: preserve `.pending.json` and investigate its trace; never
  remove it merely to repeat a POST or approval.
- Stale lock: confirm its process stopped, inspect state/live evidence, then
  remove only that exact lock. Backups omit process locks.
- Reset: use a new conversation filename; approvals are bound to the latest
  response in the original conversation.
- Cleanup: validate live owner, config fingerprint, version and digest; DELETE
  only that version and its sessions. Independently check absence even on
  repeated cleanup. Never DELETE the parent; deleting its last version can
  make the parent disappear. Shared resources and other versions are not
  targeted. Checkpoint/monitoring retention is a separate responsibility.
- Lost/stale backup: inspect the assigned live version and traces with the
  facilitator. Do not infer ownership from a name or blindly recreate it.

The hosting library owns the exporter; graph callbacks share its provider.
Inspect actual hosting/model/tool spans and results, not just answer text.
Interrupt spans can be unsuccessful without a remote result; duplicated
instrumentation does not imply duplicated business calls. Known upstream
callback warnings and qualification limits are in [VALIDATION.md](VALIDATION.md).

If public GHCR is conclusively incompatible in the target region, a separately
authorized operator may import the same digest into one shared ACR. Do not
rebuild, introduce a registry per seat or weaken network policy.

## Developer checks

Python is required only for runtime development, not the attendee deployment.
From a prepared Python 3.13/uv development environment:

```powershell
uv sync --project student\labs\hosted-agent --locked
uv run --project student\labs\hosted-agent python -m pytest student\labs\hosted-agent\tests
pwsh -NoProfile -File student\labs\hosted-agent\tests\test_rest.ps1
```

The approved feed, hashed production requirements and existing uv lock remain
unchanged. Regenerate both deliberately after a dependency change. The older
`scripts/lab07.py` and `scripts/invoke.py` remain SDK operator alternatives;
they are not the lab's core path. Image source, Dockerfile and GitHub Actions
publication are unchanged by the Cloud Shell delivery decision.
