"""Bounded, ownership-scoped Azure Express deployment, reset and cleanup."""
import argparse
import json
import os
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
API = "2026-07-01"
PURPOSE = "foundry-workshop-mcp"
ENVIRONMENT = "foundry-mcp-express"
APPS = {"partners": "foundry-mcp-partners", "complaints": "foundry-mcp-complaints"}
STATE = ROOT / ".deployment.json"
LOCK = ROOT / ".operation.lock"
ARM = "https://management.azure.com"


def az(*args):
    command = ["az", *args]
    if os.name == "nt":
        command[0] = "az.cmd"
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError(f"Azure CLI failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


@contextmanager
def operation_lock():
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("Another operation or recovery marker exists. Check .operation.lock PID and cloud state before removing it.") from exc
    with os.fdopen(fd, "w") as file:
        json.dump({"pid": os.getpid(), "started_at": time.time()}, file)
    try:
        yield
    except BaseException:
        print(f"Operation incomplete. Recovery marker retained: {LOCK}. Inspect the exact resources reported above before retrying.")
        raise
    else:
        LOCK.unlink()


class Azure:
    def __init__(self, subscription):
        self.subscription = subscription
        self.token = az("account", "get-access-token", "--subscription", subscription,
                        "--resource", ARM, "-o", "json")["accessToken"]
        self.key = ""

    def request(self, method, path, body=None, missing=False):
        if path.startswith("https://"):
            parsed = urlsplit(path)
            if parsed.scheme != "https" or parsed.netloc != "management.azure.com":
                raise RuntimeError("Refusing ARM pagination outside the management endpoint")
            url = path
        else:
            version = "2022-09-01" if "/providers/" not in path else API
            url = f"{ARM}{path}{'&' if '?' in path else '?'}api-version={version}"
        data = json.dumps(body).encode() if body is not None else None
        request = Request(url, data=data, method=method,
                          headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        for attempt in range(4):
            try:
                with urlopen(request, timeout=90) as response:
                    value = response.read()
                    return json.loads(value) if value else {}
            except HTTPError as exc:
                if missing and exc.code == 404:
                    return None
                message = exc.read().decode(errors="replace")
                for secret in (self.token, self.key):
                    if secret:
                        message = message.replace(secret, "[REDACTED]")
                correlation = exc.headers.get("x-ms-correlation-request-id", "not supplied")
                if exc.code in {429, 500, 502, 503, 504} and attempt < 3:
                    time.sleep(min(30, 2 ** (attempt + 1)))
                    continue
                raise RuntimeError(f"ARM {method} {path}: HTTP {exc.code}; correlation {correlation}; {message}") from None
            except (URLError, TimeoutError):
                # Never blindly retry a mutation with an uncertain outcome.
                if method == "GET" and attempt < 3:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise RuntimeError(f"ARM {method} {path}: transport failure; inspect this exact resource before retrying") from None

    def wait(self, path, absent=False):
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            resource = self.request("GET", path, missing=True)
            if absent and resource is None:
                return
            if not absent and resource:
                state = resource.get("properties", {}).get("provisioningState")
                if state == "Succeeded":
                    return resource
                if state in {"Failed", "Canceled"}:
                    raise RuntimeError(f"Provisioning {state}: {path}. Inspect ARM operation diagnostics.")
            time.sleep(5)
        raise TimeoutError(f"Timed out waiting for {path}; resource may remain")


def owned(resource, resource_id):
    if resource and resource.get("tags", {}).get("purpose") != PURPOSE:
        raise RuntimeError(f"Refusing unowned resource: {resource_id}")


def health(url):
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        try:
            with urlopen(url.removesuffix("/mcp") + "/healthz", timeout=30) as response:
                if json.load(response).get("status") == "ok":
                    return
        except (URLError, TimeoutError):
            time.sleep(3)
    raise TimeoutError(f"Health timeout: {url}; inspect Express logs and image pull status")


def public_image(image):
    match = re.fullmatch(r"ghcr\.io/([a-z0-9_-]+)/foundry-workshop-mcp-(partners|complaints):sha-([0-9a-f]{40})", image)
    if not match:
        raise ValueError("Use an immutable ghcr.io/<owner>/foundry-workshop-mcp-<service>:sha-<40-character-commit> image")
    repository = image.removeprefix("ghcr.io/").split(":")[0]
    tag = image.split(":")[1]
    token_url = f"https://ghcr.io/token?service=ghcr.io&scope=repository:{repository}:pull"
    try:
        with urlopen(token_url, timeout=30) as response:
            token = json.load(response)["token"]
        request = Request(f"https://ghcr.io/v2/{repository}/manifests/{tag}",
                          headers={"Authorization": f"Bearer {token}",
                                   "Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json"})
        with urlopen(request, timeout=30) as response:
            manifest = json.load(response)
            if manifest.get("schemaVersion") != 2:
                raise RuntimeError(f"Invalid image manifest: {image}")
    except HTTPError as exc:
        raise RuntimeError(f"Anonymous GHCR pull denied for {image}: HTTP {exc.code}. Set this package public in GitHub package settings.") from None


def app_body(location, environment_id, image, key):
    return {
        "location": location, "tags": {"purpose": PURPOSE},
        "properties": {
            "environmentId": environment_id,
            "configuration": {
                "activeRevisionsMode": "Single",
                "ingress": {"external": True, "targetPort": 8000, "transport": "http", "allowInsecure": False},
                "secrets": [{"name": "mcp-api-key", "value": key}],
            },
            "template": {
                "containers": [{
                    "name": "mcp", "image": image,
                    "resources": {"cpu": 0.25, "memory": "0.5Gi"},
                    "env": [{"name": "MCP_API_KEY", "secretRef": "mcp-api-key"}],
                    "probes": [
                        {"type": "Liveness", "httpGet": {"path": "/healthz", "port": 8000}, "periodSeconds": 30},
                        {"type": "Readiness", "httpGet": {"path": "/healthz", "port": 8000}, "periodSeconds": 10},
                        {"type": "Startup", "httpGet": {"path": "/healthz", "port": 8000},
                         "periodSeconds": 5, "failureThreshold": 30},
                    ],
                }],
                "scale": {"minReplicas": 0, "maxReplicas": 1,
                          "rules": [{"name": "http", "http": {"metadata": {"concurrentRequests": "20"}}}]},
            },
        },
    }


def run(args):
    account = az("account", "show", "-o", "json")
    subscription = args.subscription or account["id"]
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", subscription):
        raise ValueError("Supply the exact subscription UUID")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", args.resource_group):
        raise ValueError("Invalid dedicated resource group name")
    api = Azure(subscription)
    scope = f"/subscriptions/{subscription}/resourceGroups/{args.resource_group}"
    env_id = f"{scope}/providers/Microsoft.App/managedEnvironments/{ENVIRONMENT}"
    ids = {service: f"{scope}/providers/Microsoft.App/containerApps/{name}" for service, name in APPS.items()}
    print(f"Scope: {scope}; environment {ENVIRONMENT}; apps {', '.join(APPS.values())}; action {args.action}")
    existing_group = api.request("GET", scope, missing=True)
    owned(existing_group, scope)
    existing_env = api.request("GET", env_id, missing=True) if existing_group else None
    owned(existing_env, env_id)
    existing_apps = {}
    for service, identifier in ids.items():
        existing_apps[service] = api.request("GET", identifier, missing=True) if existing_group else None
        owned(existing_apps[service], identifier)
    if existing_env and existing_env["properties"].get("environmentMode") != "Express":
        raise RuntimeError("Refusing to use a non-Express environment")

    if args.action == "cleanup":
        if not args.confirm:
            raise ValueError("Cleanup requires --confirm; it deletes only the two owned apps and owned Express environment")
        # Refuse environment deletion if it contains any app outside this contract.
        apps = []
        next_page = f"{scope}/providers/Microsoft.App/containerApps" if existing_group else None
        seen = set()
        while next_page:
            if next_page in seen:
                raise RuntimeError("ARM pagination loop; refusing cleanup")
            seen.add(next_page)
            page = api.request("GET", next_page)
            apps.extend(page["value"])
            next_page = page.get("nextLink")
        extras = [item["id"] for item in apps
                  if item["properties"].get("environmentId", "").lower() == env_id.lower()
                  and item["id"].lower() not in {value.lower() for value in ids.values()}]
        if extras:
            raise RuntimeError(f"Environment contains unrelated apps; refusing cleanup: {extras}")
        for service, identifier in ids.items():
            if existing_apps[service]:
                api.request("DELETE", identifier)
                api.wait(identifier, absent=True)
                print(f"Deleted {identifier}")
        if existing_env:
            api.request("DELETE", env_id)
            api.wait(env_id, absent=True)
            print(f"Deleted {env_id}")
        STATE.unlink(missing_ok=True)
        print(f"Retained resource group: {scope}; no group-wide delete was performed.")
        return

    if args.action == "reset":
        if not args.confirm:
            raise ValueError("Reset requires --confirm; all in-memory edits in both apps will be lost")
        if not existing_env or not all(existing_apps.values()):
            raise RuntimeError("Both owned apps must exist before reset")
        for service, identifier in ids.items():
            api.request("POST", identifier + "/stop")
            api.request("POST", identifier + "/start")
            url = "https://" + existing_apps[service]["properties"]["configuration"]["ingress"]["fqdn"] + "/mcp"
            health(url)
            print(f"Reset {service}: {url}")
        return

    if args.location != "swedencentral":
        raise ValueError("This delivery is validated for swedencentral; requalify Express support before using another region")
    key = os.environ.get("MCP_API_KEY") or dotenv_values(ROOT / ".env").get("MCP_API_KEY")
    if not key or len(key) < 12 or any(c.isspace() for c in key):
        raise ValueError("MCP_API_KEY must contain at least 12 non-whitespace characters")
    api.key = key
    images = {"partners": args.partners_image, "complaints": args.complaints_image}
    for service, image in images.items():
        if not image or f"foundry-workshop-mcp-{service}:" not in image:
            raise ValueError(f"Supply the {service} immutable image with --{service}-image")
        public_image(image)
    if not existing_group:
        api.request("PUT", scope, {"location": args.location, "tags": {"purpose": PURPOSE}})
    if not existing_env:
        api.request("PUT", env_id, {"location": args.location, "tags": {"purpose": PURPOSE},
                                   "properties": {"environmentMode": "Express", "publicNetworkAccess": "Enabled"}})
    environment = api.wait(env_id)
    if environment["properties"].get("environmentMode") != "Express":
        raise RuntimeError("Cloud environment is not Express")
    state = {"subscription": subscription, "resource_group": args.resource_group,
             "environment_id": env_id, "location": args.location, "images": images}
    for service, identifier in ids.items():
        api.request("PUT", identifier, app_body(args.location, env_id, images[service], key))
        resource = api.wait(identifier)
        # Express stop/start also applies changed manual secrets to a running process.
        if existing_apps[service]:
            api.request("POST", identifier + "/stop")
            api.request("POST", identifier + "/start")
        props = resource["properties"]
        if props.get("environmentId", "").lower() != env_id.lower():
            raise RuntimeError(f"Wrong Express environment for {identifier}")
        if props["template"]["scale"]["maxReplicas"] != 1:
            raise RuntimeError(f"Unsafe replica count for volatile data: {identifier}")
        url = "https://" + props["configuration"]["ingress"]["fqdn"] + "/mcp"
        health(url)
        state[f"{service}_url"] = url
        state[f"{service}_id"] = identifier
        print(f"Ready {service}: {url}")
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(STATE)
    print(f"Saved nonsecret deployment settings: {STATE}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["deploy", "reset", "cleanup"])
    parser.add_argument("--subscription")
    parser.add_argument("--resource-group", default="rg-foundry-mcp-lab")
    parser.add_argument("--location", default="swedencentral")
    parser.add_argument("--partners-image")
    parser.add_argument("--complaints-image")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    with operation_lock():
        run(args)


if __name__ == "__main__":
    main()
