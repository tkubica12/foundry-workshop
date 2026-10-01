# Knowledge-base lab

[HTML guide](../../../docs/guides/chapter-5-knowledge-base.html) ·
[Reference data](../../../evals/grounding/) ·
[Qualification evidence](VALIDATION.md)

## Isolated live rehearsal

Supported operator platform: Windows, Python 3.13+, Azure CLI and Windows curl.
Authenticate explicitly with `az login`, choose an authorized subscription, and
confirm permission to create resources and resource-scoped role assignments.
No Python packages or SDK installation is required. Paid Search, model inference,
embeddings and evaluation usage apply. This is an operator rehearsal, not an
attendee setup command.

From the repository root:

```powershell
python evals\grounding\prepare.py --bundle
python student\labs\knowledge-base\scripts\azure.py deploy --state .workshop\knowledge-base\rehearsal\state.json --subscription <subscription-id> --tier basic --search-region westeurope
python student\labs\knowledge-base\scripts\azure.py prepare --state .workshop\knowledge-base\rehearsal\state.json
python student\labs\knowledge-base\scripts\azure.py evaluate --state .workshop\knowledge-base\rehearsal\state.json --phase baseline --limit 5
python student\labs\knowledge-base\scripts\azure.py evaluate --state .workshop\knowledge-base\rehearsal\state.json --phase baseline --limit 20
python student\labs\knowledge-base\scripts\azure.py evaluate --state .workshop\knowledge-base\rehearsal\state.json --phase candidate --limit 20
python student\labs\knowledge-base\scripts\azure.py evaluate --state .workshop\knowledge-base\rehearsal\state.json --phase baseline
python student\labs\knowledge-base\scripts\azure.py evaluate --state .workshop\knowledge-base\rehearsal\state.json --phase candidate
python student\labs\knowledge-base\scripts\azure.py verify --state .workshop\knowledge-base\rehearsal\state.json
```

The first command verifies PDF hashes and builds exact attendee download assets.
`--limit 20` uses the balanced core file: one case per dossier and four per
evidence type. Other nonzero limits use prefixes for smoke testing; omit the
limit for the full 100. Saved run fingerprints prevent resuming against changed
references, and strict row checks require complete answers and both scores.
The command deliberately selects the tested Basic/West Europe combination,
with models in Sweden Central. The script's unqualified default remains
Serverless Search in Sweden Central; do not omit the explicit flags for this
rehearsal. Neither documented regional support nor a previous deployment
guarantees current capacity. If creation is
rejected, reconcile the resource list first. If no Search resource exists, an
explicit retry can use `deploy ... --tier basic --search-region westeurope`.
The script refuses migration after Search exists. Region and cost changes must
be authorized by the operator; it does not automatically fan out across regions
or tiers.

Preparation uses minimal text extraction, `text-embedding-3-small` version `1`,
and `gpt-5-mini` version `2025-08-07` for planning, answering and judging.
These pinned deployment versions were admitted during this rehearsal; check
current admission and quota before another clean deployment. Keys are disabled.
The Search service calls models under its own managed identity; the agent uses
the project identity and only the vetted `knowledge_base_retrieve` MCP tool.
Reference fields are not sent to the target agent.

## Delivery preflight

Prepare the assigned Search service and all 20 minimal-extraction PDFs before
the session. The core guide selects the existing source, then creates and
attaches a KB to the attendee's baseline agent. Native bulk upload is optional:
the student rehearsal needed two failed-file-only retries for HTTP 429.
`prepare` uploads sequentially, reconciles existing filenames and verifies the
real cited answer. Require `prepare`/`verify` to pass the exact inventory of
20 distinct corpus filenames before delivery; neither file nor chunk counts
alone certify it. Do not introduce shared Blob storage as a delivery fallback.

The observed student account had Owner on its isolated resource group,
Foundry User and Search Index Data Contributor. This is a personal-group
workshop contract, not proof of a least-privilege authoring profile.

| Principal | Required access and scope |
| --- | --- |
| Attendee author | Search Service Contributor for Search object authoring; Search Index Data Contributor for uploads, on the assigned Search service |
| Attendee agent author | Foundry User plus connection-management permission; the tested account inherited control-plane access from its personal-group Owner assignment |
| Foundry project managed identity | Search Index Data Reader on the assigned Search service |
| Search system-assigned managed identity | Cognitive Services User on the resource hosting embedding/planning deployments |

Owner alone does not provide direct Search object/content permissions. Author permissions do not
replace either managed-identity assignment. Keep Search and Foundry local
authentication disabled; the portal must show Project Managed Identity for
the Search connection and the keyless notice for planning/embeddings.
If model resources are shared, the operator assigns every prepared Search
identity before delivery; attendees need no Owner permission on that shared
group. Verify with the actual attendee identity, not only the operator.

Check region support and quota separately. Spain Central's current Search
matrix does not list agentic retrieval or AI enrichment; it is not an approved
fallback for this lab. Sweden Central lists agentic retrieval but has rejected
new Search services for capacity. Admit and verify the complete room before
delivery, including model/judge throughput and permission propagation.

The separate standard-extraction REST probe used Search API
`2026-08-01-preview`, `contentExtractionMode: standard`, the Foundry
`services.ai.azure.com` endpoint in `aiServices.uri`, and the existing
`chatCompletionModel` and `embeddingModel`; every API key and explicit
`authIdentity` was omitted. The same Search system identity was authorized on
Foundry. One PDF produced image-derived chart evidence and a cited answer.
This is not implemented by `prepare`, exposed by the native file dialog, or a
full-corpus qualification. Keep it outside the core and use a separate source.

## Recovery and destructive scope

Every command prints its exact resource-group scope. State, run IDs and raw
diagnostics remain in ignored `.workshop`. GET retries are bounded. Mutations
are not blindly retried after transport failure. Reconcile failed operations
before resuming; for interrupted file uploads, allow the documented 180-second
processing window to elapse, list files, and retry only absent filenames.
Uploads do not replace same-name files. Duplicate names fail verification.
An unsuccessful run is not counted as a low score.

Repeating preparation retains saved agent versions and verifies all 20 file
names in the index, not just a chunk count. Repeating `evaluate` resumes the
saved run for that phase and row count; it never submits a duplicate. To perform
a deliberately new independent experiment, use a new state path and group.
If `.lock` remains after a process crash, inspect the recorded PID and cloud
operations before removing that specific lock file.

Export results before cleanup. Read the exact generated group name in state,
then run:

```powershell
python student\labs\knowledge-base\scripts\azure.py cleanup --state .workshop\knowledge-base\rehearsal\state.json --confirm-group <exact-generated-group-name>
```

Cleanup checks ownership tags and refuses unexpected resources before deleting
the private rehearsal group. It verifies absence, retains local results and
reports any pending deletion. It does not purge a soft-deleted Foundry account.
Never use this cleanup workflow on attendee/shared workshop resources.
