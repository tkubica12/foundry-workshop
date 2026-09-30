# MCP backend operator contract

Backend assets for the planned tools chapter, not a complete attendee lab.
Two independent Python services: **120 fictional authorized service partners**
and **90 synthetic complaints**. Real city/street geography is combined with
invented premises, contacts and organizations. Coordinates are city centers,
not verified service locations. `.example` email/web addresses and telephone
numbers are intentionally nonoperational.

## Runtime

FastMCP **4.0.5**, Python **3.13.15**, Streamable HTTP at `/mcp`, both modern
and legacy MCP negotiation. Health is public at `/healthz` and returns no records.
Every MCP request requires `Authorization: Bearer <MCP_API_KEY>`.
Set the key at process/container startup; missing or invalid configuration
fails startup. There is no fallback key, OAuth discovery, database or outbound
service dependency. The shared key grants all tools, including deletion.
Use only synthetic records; rotate to a random 32+ character secret before any
broader use. Do not share `.env`, command transcripts containing secrets or
deployment settings.

**All writes are volatile and shared between clients.** One process, one worker,
maximum one Azure replica. Restart, redeployment and scale-to-zero can restore
the seed data. Do not use this backend for durable storage or concurrent
independent attendee exercises. Mutations require the current `version`;
fetch again after a conflict. PUT replaces the complete partner, POST creates
a generated ID. Exact-repeat PUT preserves the version.

| Service | Tools |
| --- | --- |
| Partners | `get_partner`, `list_partners`, `search_partners`, `create_partner`, `put_partner`, `delete_partner` |
| Complaints | `get_complaint`, `list_complaints`, `search_complaints`, `create_complaint`, `update_complaint`, `assign_complaint`, `add_complaint_note`, `transition_complaint`, `complaint_statistics`, `delete_complaint` |

Search filters use AND, text matches are case-insensitive, pages contain
`items`, `total`, `offset`, `limit`, `next_offset`. Limit is 1-100.
Partner filters include country, city, authorization status, tier, specialty,
language, emergency availability, rating and capacity. Complaint filters include
customer email, country, category, priority, lifecycle status, assigned partner
and overdue state. Discover precise argument schemas using `tools/list`.

Complaint transitions: new -> triaged -> in_progress -> awaiting_customer or
resolved -> closed. Awaiting_customer can return to in_progress or resolve;
resolved can reopen to in_progress; closed can reopen to triaged.
Resolution is mandatory when resolving, and reopening clears it.
Assignment stores a reference only: verify the partner exists and is active
with Partner MCP first. Partner deletion does not cascade into complaints.
Cases retain timestamped notes/history. Record counts are bounded at 2,000;
each case allows 100 notes and 100 transitions.

## Prepare and verify locally

Supported operator hosts: Windows PowerShell with Python 3.13, `uv`, `az` and
`gh`; CI and containers run Linux. Azure CLI must already be signed in with
write permission in the intended subscription. No Docker daemon is required on
the operator workstation; GitHub Actions builds and exercises the containers.
Run from the repository root:

```powershell
uv sync --project student\labs\mcp-services --frozen
Copy-Item student\labs\mcp-services\.env.example student\labs\mcp-services\.env
# Set MCP_API_KEY in the ignored .env using your local editor.
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\mcp-services\scripts\test_local.py
```

Do not overwrite an existing `.env`. The dependency index is explicitly the
approved Microsoft proxy in the isolated project; the root project's dependency
manifest and lock are not changed. `uv.lock` covers Windows/Linux;
`requirements.lock` is its hashed, frozen export for image builds.
After a deliberate dependency upgrade, regenerate using
`uv export --project student\labs\mcp-services --frozen --no-dev --no-emit-project --format requirements-txt --output-file student\labs\mcp-services\requirements.lock`.

For manual local serving, load the key into `MCP_API_KEY` in your shell without
printing it, change to this directory and run the virtualenv's Python:
`python -m uvicorn services.partners:app --host 127.0.0.1 --port 8001 --workers 1`.
Use `services.complaints:app` and port 8002 for the other service.
Dockerfiles install locked dependencies, copy only code and run as UID 10001.

## Publish

The [workflow](../../../../.github/workflows/publish-mcp.yml) builds and tests
two separate images, then publishes immutable `sha-<commit>` and convenience
`latest` tags. It runs on scoped changes pushed to `main` or manual dispatch:

```powershell
gh workflow run publish-mcp.yml --ref main
gh run list --workflow publish-mcp.yml --limit 5
```

The workflow authenticates publication with ephemeral `GITHUB_TOKEN` and
`packages: write`. Anonymous publication is not supported by GHCR.
**Anonymous pulling requires each package to be public**, independently of the
repository visibility. After the initial run, open your GitHub profile ->
Packages -> `foundry-workshop-mcp-partners` / `foundry-workshop-mcp-complaints` ->
Package settings -> Change visibility -> Public. Do not put registry credentials
in the Azure apps. Deployment preflights an anonymous token exchange and image
manifest retrieval for both exact tags before it creates any cloud resources.

## Deploy to Azure Express

Azure Express availability and API behavior were checked on **2026-09-30**:
[supported features/regions](https://learn.microsoft.com/azure/container-apps/express-overview),
[ARM environment schema](https://learn.microsoft.com/azure/templates/microsoft.app/2026-07-01/managedenvironments).
This delivery uses Sweden Central, ARM `2026-07-01`, one Express environment,
two externally reachable HTTPS apps, 0.25 vCPU/0.5 GiB each, min 0/max 1 replica.
No ACR, database, storage account, VNet or managed identity is required.
Compute and transfer incur ongoing Azure charges; scale-to-zero is not a
guarantee of a zero total bill. Obtain authorization before creating resources.

```powershell
$owner = gh api user --jq .login
$sha = git rev-parse HEAD
$subscription = az account show --query id -o tsv
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\mcp-services\scripts\azure.py deploy --subscription $subscription --partners-image "ghcr.io/$owner/foundry-workshop-mcp-partners:sha-$sha" --complaints-image "ghcr.io/$owner/foundry-workshop-mcp-complaints:sha-$sha"
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\mcp-services\scripts\verify.py
```

Use the actual published workflow commit, not HEAD if it has moved.
The default dedicated group is `rg-foundry-mcp-lab`; the script checks ownership
tags before using existing resources and refuses non-Express environments.
It reads the key from the ignored `.env` (or `MCP_API_KEY` environment variable),
sends it to ARM over TLS in memory, and configures an Azure manual secret
referenced by the container. Secrets are never command arguments or state.
On updates the script stops/starts the Express apps to apply changed secrets.
Repeat deployment retains resource IDs but resets runtime edits.

Expected results: both ready HTTPS `/mcp` URLs, actual
`environmentMode=Express`, an ignored `.deployment.json`, and PASS lines for
all 6 + 10 tools in modern and legacy modes. `verify.py` runs from your
workstation against the deployed endpoints, checks unauthenticated/incorrect
keys on GET/POST/DELETE, pagination/filtering, create/get/update/delete,
version conflicts, notes, all lifecycle branches and error paths.
It creates isolated test records and removes them in `finally`; it never
modifies seeded cases. Run one verifier at a time without concurrent lab
mutations because it also checks exact before/after totals.

## Reset, recovery and cleanup

```powershell
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\mcp-services\scripts\azure.py reset --subscription $subscription --confirm
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\mcp-services\scripts\verify.py
student\labs\mcp-services\.venv\Scripts\python.exe student\labs\mcp-services\scripts\azure.py cleanup --subscription $subscription --confirm
```

Reset destroys runtime edits and reloads fixtures. Cleanup deletes only the two
owned apps and their owned Express environment, refuses unrelated apps in that
environment, and **retains the resource group and GHCR packages**.
Inspect/remove the empty resource group separately only with authorization.
Always pass the original subscription/group, not a changed CLI default.

| Symptom | Action |
| --- | --- |
| Anonymous GHCR manifest denied | Make both exact packages public; rerun before deployment. |
| ARM 403 | Check the selected subscription and operator role; do not broaden permissions automatically. |
| Provisioning/image-pull failure | Inspect the exact named resource and Express log stream; preserve the printed provider correlation ID. |
| Transport timeout during a mutation | Inspect cloud state before retrying; the operation may already have succeeded. |
| `.operation.lock` exists | Read its PID, verify no operator is active and inspect the exact resource state. Remove only that marker after recovery, then repeat the same deploy command. |
| MCP 401 | Check the local key matches Azure secret. Rotate via `.env` and repeat deploy; do not print either secret. |
| Version conflict | Fetch the latest record/version; do not blindly overwrite another client's changes. |
| Seed data returns unexpectedly | Memory was reset by restart/scale-to-zero; rerun the full case journey. |

Provisioning polls are bounded to 15 minutes/resource, health to 5 minutes,
ARM requests to 90 seconds with at most four attempts for throttling/transient
server failures. A failed operation exits nonzero and retains a nonsecret
recovery marker. Deployment settings are written only after both apps are healthy;
the deterministic resource names above identify any partial deployment.
