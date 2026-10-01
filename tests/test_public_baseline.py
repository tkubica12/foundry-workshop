"""Keep the public baseline independent of customer identities and private state."""

from pathlib import Path
import re
import subprocess
import tomllib


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".html", ".css", ".js", ".py", ".ps1", ".json", ".jsonl", ".txt", ".toml", ".lock"}
CUSTOMER_CONTEXT = re.compile(
    r"\b(?:dr[\W_]*ma[x]|pen[t]a|labte[s]t|aihor[i]zons|BRN[O]-042|OSTRA[V]A-017)\b",
    re.IGNORECASE,
)


def public_files():
    roots = {"docs", "student", "teacher", "templates", "tests"}
    names = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
    ).decode("utf-8").split("\0")
    files = [ROOT / name for name in names if name and (
        len(Path(name).parts) == 1 or Path(name).parts[0] in roots
    )]
    return [
        path for path in files
        if path.is_file() and not any(part in {"__pycache__", ".pytest_cache", "evidence"} for part in path.parts)
    ]


def test_text_has_no_original_customer_or_environment_context():
    violations = []
    for path in public_files():
        if path.suffix in TEXT_SUFFIXES:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if CUSTOMER_CONTEXT.search(line):
                    violations.append(f"{path.relative_to(ROOT)}:{number}")
    assert not violations, violations


def test_package_identity_and_lockfile_agree():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    assert project["project"]["name"] == "foundry-workshop"
    root_package = [item for item in lock["package"] if item.get("source") == {"virtual": "."}]
    assert len(root_package) == 1
    assert root_package[0]["name"] == project["project"]["name"]


def test_no_private_state_or_retired_capture_is_distributed():
    assert not list((ROOT / "docs" / "assets" / "screenshots").glob("*.png"))
    forbidden_suffixes = {".tfstate", ".tfplan", ".psd1"}
    for path in public_files():
        assert path.suffix not in forbidden_suffixes, path
        assert path.name not in {".env", "state.json", "credentials.json", "terraform.tfvars"}, path


def test_no_ui_captures_or_capture_galleries_are_published():
    assets = ROOT / "docs" / "assets"
    assert not list(assets.rglob("*.png"))
    for path in (ROOT / "docs" / "guides").glob("*.html"):
        source = path.read_text(encoding="utf-8")
        assert "walkthrough/" not in source
        assert "Screenshot" not in source
        assert "<img" not in source


def test_one_day_scope_and_honest_publication_boundary():
    agenda = (ROOT / "AGENDA.md").read_text(encoding="utf-8")
    assert "09:00-17:00" in agenda
    assert "30-minute core path" in agenda
    assert "55 minutes" in agenda
    assert "not published" in agenda
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Labs 1 through 6 and optional Lab 7 have published guides" in readme
    assert "portal journey still needs an attendee-identity rehearsal" in readme
    assert "handoffs" not in readme


def test_text_line_endings_are_explicit_for_reproducible_lab_inputs():
    assert (ROOT / ".gitattributes").read_text(encoding="utf-8").strip() == "* text=auto eol=lf"
