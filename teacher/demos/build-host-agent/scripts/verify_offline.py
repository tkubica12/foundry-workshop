"""Run the six trusted Chapter 2 test modules with local-only guardrails.

Use the prepared repository Python environment. This is not a security sandbox
for untrusted Python code. Browser and PDF tests deliberately run separately.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
TEST_MODULES = (
    "test_build_host_agent.py",
    "test_lab_cleanup.py",
    "test_lab_contract.py",
    "test_lab_next_step.py",
    "test_lab_scorecard.py",
    "test_lab_seat_contract.py",
)
BLOCKED_EVENTS = frozenset({
    "socket.connect", "socket.bind", "socket.getaddrinfo", "socket.gethostbyname",
    "socket.gethostbyaddr", "socket.getnameinfo", "socket.sendto", "socket.sendmsg",
    "subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.fork",
    "os.forkpty", "os.spawn", "os.startfile", "os.startfile/2",
})
ENV_PREFIXES = ("WORKSHOP_", "AZURE_", "FOUNDRY_", "OPENAI_", "OTEL_")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--root", type=Path, default=REPO_ROOT,
        help="optional assertion of the checkout root; must match this script",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if root != REPO_ROOT:
        parser.error("--root must match the checkout containing this verifier")
    paths = [root / "tests" / module for module in TEST_MODULES]
    if not (root / "AGENTS.md").is_file() or not all(path.is_file() for path in paths):
        parser.error("the checkout must contain AGENTS.md and all six Chapter 2 test modules")

    original_seat = os.environ.get("WORKSHOP_SEAT_FILE")
    protected_files = {
        (root / ".workshop-live.psd1").resolve(),
        (root / "teacher" / "demos" / "build-host-agent" / ".live-demo.psd1").resolve(),
        Path("/etc/workshop/seat.env").resolve(),
    }
    if original_seat:
        protected_files.add(Path(original_seat).resolve())
    protected_dirs = (
        (root / ".workshop").resolve(),
        (root / ".terraform").resolve(),
    )
    violations: set[str] = set()

    def deny_external(event: str, event_args: tuple) -> None:
        # urllib3 probes IPv6 support by binding ::1:0 during SDK import.
        if event == "socket.bind" and event_args[1] in {("::1", 0), ("127.0.0.1", 0)}:
            return
        if event in BLOCKED_EVENTS:
            violations.add(event)
            raise RuntimeError(f"offline verification forbids {event}")
        if event == "open" and isinstance(event_args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(event_args[0])).resolve()
            name = path.name.lower()
            if (
                path in protected_files
                or any(path.is_relative_to(directory) for directory in protected_dirs)
                or name == ".env" or name.startswith(".env.")
                or ".tfstate" in name or name.endswith(".tfplan")
                or name == "terraform.tfvars" or name.endswith(".auto.tfvars.json")
            ):
                violations.add("real configuration/state access")
                raise RuntimeError("offline verification forbids real configuration/state access")

    os.chdir(root)
    sys.path.insert(0, str(root))
    sys.dont_write_bytecode = True
    for key in list(os.environ):
        if key.startswith(ENV_PREFIXES) or key in {
            "SEAT_ID", "WORKSHOP_PLATFORM_REPO", "PYTEST_ADDOPTS", "PYTEST_PLUGINS",
        }:
            del os.environ[key]
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    sys.addaudithook(deny_external)

    try:
        import dotenv
        import dotenv.main
        import pytest
    except ImportError as error:
        parser.exit(2, f"Prepared repository dependencies are required: {error}\n")

    def disabled_load_dotenv(*_args, **_kwargs) -> bool:
        return False

    # The agent imports load_dotenv at module load; disable both public aliases.
    dotenv.load_dotenv = disabled_load_dotenv
    dotenv.main.load_dotenv = disabled_load_dotenv

    class Isolation:
        @pytest.fixture(autouse=True)
        def isolate(self, monkeypatch, tmp_path):
            for name in ("chapter2_demo", "seat"):
                module = sys.modules.get(name)
                if module is None:
                    continue
                if name == "chapter2_demo":
                    monkeypatch.setattr(module, "STATE_ROOT", tmp_path)
                    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "demo-state.json")
                else:
                    monkeypatch.setattr(module, "SEAT_ENV_FILE", tmp_path / "absent.env")

        def pytest_sessionfinish(self, session, exitstatus):
            reporter = session.config.pluginmanager.get_plugin("terminalreporter")
            if reporter is not None and reporter.stats.get("skipped"):
                reporter.write_sep("!", "offline verification forbids skipped checks")
                session.exitstatus = pytest.ExitCode.TESTS_FAILED

    print(f"Offline verification target: {root}", flush=True)
    print(
        "Scope: six Chapter 2 modules; network/process guards active; "
        "dotenv disabled; real state blocked; synthetic per-test paths.",
        flush=True,
    )
    result = pytest.main(
        [*(str(path) for path in paths), "-q", "--noconftest", "-o", "addopts="],
        plugins=[Isolation()],
    )
    if violations:
        print("Forbidden attempts: " + ", ".join(sorted(violations)), file=sys.stderr)
        return 1
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
