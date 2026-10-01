# Optional Lab 07: code-first Hosted Agent

Source: `agent.py`, `system-prompt.txt`; delivery: `Dockerfile` and
`.github/workflows/publish-hosted-agent.yml`. This exercise is intentionally
read-only: all seven Lab 4 tools are discovered, extra tools are filtered,
each read is interrupted for approve-once, and writes fail before MCP execution.

## Operator preparation

Supported operator platforms: Windows PowerShell or Linux with Python 3.13,
uv and Azure CLI. Container platform: Linux/amd64. Docker is not needed locally.
Sign in to the authorized subscription. Use an existing compatible model,
the Lab 4 version-pinned toolbox (or both existing MCP services with a prepared
Foundry credential connection), and connected Application Insights.
The deployer needs Foundry Project Manager. The runtime agent identity needs
model and toolbox access; it is distinct from the project identity. Do not
grant broad subscription roles to repair a denied call.

From the repository root:

```powershell
uv sync --project student\labs\hosted-agent --locked
uv run --project student\labs\hosted-agent python -m pytest student\labs\hosted-agent\tests
```

The approved feed is configured explicitly in `pyproject.toml`. The hashed
production export and uv lock must stay synchronized. Regenerate after an
intentional dependency change:

```powershell
uv export --project student\labs\hosted-agent --no-dev --no-emit-project --format requirements-txt --output-file student\labs\hosted-agent\requirements.lock
```

Run the **Publish workshop Hosted Agent** workflow on the authorized commit.
The job builds the real image, runs an offline Responses approval/rejection
fixture, publishes the SHA tag, verifies anonymous pulling, and records the
immutable digest in the `hosted-agent-image` artifact. A newly created GHCR
package may require the package owner to set **Package settings > Change
visibility > Public**; a failed anonymous pull is a failed publication, not
permission to use registry credentials in the agent image.

Copy `config.example.json` to the ignored
`.workshop\hosted-agent\seat-s01.config.json`. Fill every value from your
authorized seat assignment and image receipt. Use a unique lowercase
`lab07-<run>-sNN` name. Keep the matching receipt separate. Never put a literal
MCP key in the configuration: direct-server mode uses
`${{connections.<name>.credentials.<field>}}` resolved by Foundry.
Toolbox mode uses refreshed Entra tokens.

```powershell
uv run --project student\labs\hosted-agent python student\labs\hosted-agent\scripts\lab07.py preflight --config .workshop\hosted-agent\seat-s01.config.json --state .workshop\hosted-agent\seat-s01.state.json
uv run --project student\labs\hosted-agent python student\labs\hosted-agent\scripts\lab07.py deploy --config .workshop\hosted-agent\seat-s01.config.json --state .workshop\hosted-agent\seat-s01.state.json --confirm
uv run --project student\labs\hosted-agent python student\labs\hosted-agent\scripts\lab07.py status --config .workshop\hosted-agent\seat-s01.config.json --state .workshop\hosted-agent\seat-s01.state.json
```

Preflight verifies scope and project access, not quota or runtime permissions.
Deployment records intent before a non-retried create and polls for up to ten
minutes. An active version proves infrastructure readiness only. Qualify actual
model/tool calls, approve and reject paths, both MCP services, and correlated
request/graph/model/tool spans with the intended identity before delivery.
Content recording is opt-in and permitted only with the synthetic workshop data.
The hosting library configures the exporter; the LangChain callback shares its
OpenTelemetry provider rather than creating a duplicate exporter.

## Recovery, reset and cleanup

- Timeout with a known version: run `status`, not a new deployment.
- Uncertain create without a version: inspect **Build > Agents** or list versions
  through the SDK. Verify `lab07_owner` and `lab07_config` against the retained
  receipt before recovering its version. Never blindly create a second version.
- A held `.lock`: wait for the owning command. After a confirmed terminated
  process, inspect the receipt and live agent before removing that exact lock.
- Reset: start a new conversation. Pending approval remains bound to its original
  conversation; never replay it against another response.
- Cleanup: confirm the exact receipt below. The script refuses different owners
  and deletes only the recorded immutable version, including its sessions.
  It retains the parent agent shell, any other versions, all shared MCP backends, toolbox, connections, roles, registry and
  published images. The platform checkpoint store has a 30-day item TTL; deletion
  of the version is not a claim that all monitoring/checkpoint data was erased.
  Data-retention cleanup is a separate facilitator responsibility.

```powershell
uv run --project student\labs\hosted-agent python student\labs\hosted-agent\scripts\lab07.py cleanup --config .workshop\hosted-agent\seat-s01.config.json --state .workshop\hosted-agent\seat-s01.state.json --confirm
```

If GHCR deployment conclusively fails because of registry incompatibility, import
the same digest server-side into one facilitator-managed ACR and use its digest
in the seat configs. Do not rebuild, create a registry per seat, weaken network
policy, or retry provisioning errors as if they established incompatibility.
An ACR fallback and its pull roles require separately confirmed operator scope.
