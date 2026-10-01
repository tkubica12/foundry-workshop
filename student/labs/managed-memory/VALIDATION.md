# Managed memory qualification, 2026-10-01

## Observed native portal journey

The owner signed in to a separate, task-only Edge profile and authorized
creation and deletion of an isolated test agent and store. Existing agents,
stores, deployments and project permissions were not changed.
Playwright drove the actual portal, not a mock or API-only substitute.
Private browser captures remain outside the published site.

The exact guide prompts and instructions were exercised with `gpt-5.6-sol`;
the extraction deployment was also `gpt-5.6-sol`, with
`text-embedding-3-large` for embeddings. These are observed deployments,
not a universal model-support guarantee. The initial default `gpt-6-luna`
rejected the playground's `reasoning.effort` parameter; it was replaced before
both successful comparison halves. The guide exposes this recovery boundary.

| Check | Observed outcome |
| --- | --- |
| No memory, seed | Agent acknowledged the apple preference and fictional snack. |
| No memory, New chat, recall | “I don't know what fruit you like, and we haven't discussed fruit in this conversation.” |
| Store creation | Native Build / Memory; profile and chat summary enabled, procedural disabled. |
| Agent attachment | Playground / Memory / Add / selected store; configure scope `{{$userId}}`, delay 30 seconds; save dialog and agent. |
| Stored profile | Memories / Kind / User profile returned `user_profile`: “The user likes apples.” |
| Profile recall, New chat | “You like apples.” |
| Stored summary | Memories / Kind / Chat summary returned `chat_summary` describing the apple preference and fictional hiking snack packed in a reusable box. |
| Summary recall, another New chat | “Yes. We discussed a fictional hiking snack: apples packed in a reusable box. You also said you like apples.” The response exposed `memory_search_call`. |
| Cleanup | Native agent deletion required typing the exact name; native store deletion displayed its exact name. Both were verified absent from refreshed lists. |

The portal was localized in Czech. Observed controls include Build / Agenti /
Novy agent / Sestavit agenta, Testovaci prostredi, Novy chat, Build / Pamet /
Vytvorit pametove uloziste, Rozsirena nastaveni, Konfigurovat uloziste pameti,
Obor, Pameti, Druh, Profil uzivatele and Souhrn chatu. The HTML includes the
accented labels as shown in the portal. English equivalents follow the
existing workshop vocabulary; this is not an independent English-locale test.

## Evidence manifest

Scope: current first-party public product documentation and direct native
portal observation. Internal records and community research were not needed
to establish this exercise's controls or behavior and were not searched.

| Source class / consulted source | Tool | Status / count | Use |
| --- | --- | --- | --- |
| Official docs: managed memory / user profile / session summary discovery | Microsoft Learn search, three bounded queries | Searched; 10 chunks per query, 30 total, with overlapping sources | Located memory usage and concepts; broad portal-specific queries did not establish the exact click path. |
| [Create and use memory](https://learn.microsoft.com/azure/foundry/agents/how-to/memory-usage) | Microsoft Learn fetch | Retrieved, one article; preview; retrieved 2026-10-01 | Scope identity fallback, delayed updates, direct commands, retention, required deployments. |
| [Memory concepts](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-memory) | Microsoft Learn search | Retrieved excerpts | User profile versus chat summary; procedural memory kept outside core. |
| LangChain memory integration excerpt | Microsoft Learn search | Consulted, unused | Not needed for a portal-only lab. |
| Native Foundry portal | Playwright / owner-authorized test browser | Observed the checks above | Actual creation, attachment, inspection, new-chat recalls and cleanup. No private identifiers published. |

## Local checks and independent review

The changed-experience selection passed 170 checks, including the Lab 6
content/copy cases, all guide reading controls, index navigation, HTML structure
and Lab 6's isolated export. Three broader checks failed on pre-existing
conditions: exact MIT-notice whitespace in Labs 4 and 5, and a local
MCP-services `.env` file counted by the public-baseline filesystem scan.
Those unrelated files and assertions were not changed or hidden.

Canonical validation passed 273/273 checks on the source at 1440x900 and
273/273 on an isolated single-file export at 1920x1080: all eight palettes,
offline rendering, no-JavaScript reading, controls and print. Mobile/desktop
light/dark copy/layout checks passed. `git diff --check` passed.
The single-file export retains sibling navigation links, which require the
workshop collection; its own reading content and runtime are self-contained.
No PDF was requested or published.

Independent role-prompted Educator/Student and safety/reproducibility reviews
inspected the actual guide and qualification record and reported no blocking
or material findings. The Educator/Student reviewer also exercised the local
guide in Edge/Playwright without errors or layout overflow. Neither review
claims an independent cloud run or fresh attendee identity.

## Remaining delivery boundaries

The 20-minute core and five-minute recovery/discussion are design targets,
not measured clean-room attendee durations. Attendee least-privilege roles,
regional availability and concurrent-seat capacity still require rehearsal.
The exercise starts from facilitator-prepared deployments. No fresh cloud
resource deployment or role assignment was performed.

New chat does not erase memory. Agent deletion alone does not certify store
deletion; store deletion does not certify deletion of traces or platform logs.
Only synthetic preferences were submitted. No production identity isolation,
cross-user access test, TTL expiry or forget-command erasure guarantee is
claimed.
