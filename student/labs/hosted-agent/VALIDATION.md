# Lab 07 qualification

Source and isolated operator evidence are not room or attendee-role qualification.
Do not advertise the lab as delivery-ready until every live gate is satisfied.
Private identifiers, response bodies, traces and environment receipts stay under
ignored `.workshop\hosted-agent`; no UI screenshots are published.

| Goal Card gate | Evidence and current boundary |
| --- | --- |
| C01: supported integration | Current Responses host; pinned approved-feed resolution; Python 3.13. |
| C02: image and protocol | Offline actual HTTP readiness, approval continuation and rejection pass. Image/CI qualification pending. |
| C03: shared tools and safety | Live operator discovery found seven expected tools. Offline allowlist, approve-once, forged-resume and write-denial tests pass. Live hosted calls pending. |
| C04: telemetry | Host exporter and graph/model/tool callback wired; live correlation and viewer journey pending. |
| C05: deployment and registry | Public GHCR preferred; actual Hosted Agent activation/invocation not yet qualified. No ACR fallback established. |
| C06: lifecycle | Offline uncertain-create, lock, owner and version-only cleanup tests pass. Live repeat/reset/cleanup pending. Parent shell and shared resources intentionally retained. |
| C07: learning and reproducibility | Safety review repaired a parent-deletion race and found no remaining material issue. Fresh learner, educator and clean-room reviews still required. |

Checks on 2026-10-01: 15 isolated Python tests passed, including actual local
Responses HTTP. Safety recheck separately passed 14 graph/lifecycle tests.
Those checks use an offline model; they do not assert live model answers,
runtime identity authorization, connected traces or attendee access.
