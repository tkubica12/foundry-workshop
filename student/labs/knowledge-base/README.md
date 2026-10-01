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
python student\labs\knowledge-base\scripts\azure.py deploy --state .workshop\knowledge-base\rehearsal\state.json --subscription <subscription-id>
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
Deployment defaults to Serverless Search in Sweden Central. If creation is
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
