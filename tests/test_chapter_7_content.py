from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guides" / "chapter-7-hosted-agent.html"


def test_cloud_shell_is_the_no_install_core_path():
    source = GUIDE.read_text(encoding="utf-8")
    assert "No storage account required" in source
    assert "az rest" in source
    assert "PowerShell" in source
    assert "uv run" not in source
    assert "python student" not in source
    assert "git clone --depth 1" in source
    assert "-Operation preflight" in source
    assert "-Operation deploy" in source


def test_ephemeral_receipts_and_safe_recovery_are_explicit():
    source = GUIDE.read_text(encoding="utf-8")
    for text in ("Manage files &rarr; Upload", "Manage files &rarr; Download",
                 "-Operation backup", "Expand-Archive", "-Operation recover-create",
                 ".pending.json", "never sends a parent-agent DELETE",
                 "Closing the shell is not agent cleanup", "newer outcome as uncertain"):
        assert text in source
    assert "It retains the agent shell" not in source


def test_approvals_traces_and_optional_code_journey_remain():
    source = GUIDE.read_text(encoding="utf-8")
    for text in ("Optional", "build_graph", "FoundryCheckpointSaver",
                 "-Operation approve", "-Operation reject", "interrupt_rejected",
                 "Trace ID", "Application Insights", "actual tool results",
                 "GitHub Actions", "complaint-003", "partner-055"):
        assert text in source
    assert 'id="resume-cleanup"' in source
    assert "YOUR-ASSIGNED-TENANT" in source
    assert "Never print an access token" in source
