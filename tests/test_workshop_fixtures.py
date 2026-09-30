"""Contract tests for the synthetic stock-operations fixture pack."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "student"
    / "labs"
    / "shared"
    / "fixtures"
    / "stock-operations-v1"
)


def load(relative: str) -> dict:
    return json.loads((FIXTURE_ROOT / relative).read_text(encoding="utf-8"))


def test_manifest_hashes_match_every_protected_file() -> None:
    manifest = load("manifest.json")
    assert manifest["fixture_id"] == "stock-operations-v1"
    assert manifest["classification"] == "synthetic workshop data only"
    for item in manifest["files"]:
        path = FIXTURE_ROOT / item["path"]
        assert path.is_file(), item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], item["path"]


def test_case_sets_are_exactly_eight_plus_four_and_separate_teacher_controls() -> None:
    development = load("cases/development.json")["cases"]
    holdout = load("cases/holdout.json")["cases"]
    teacher = load("teacher/teacher-controls.json")
    assert [case["case_id"] for case in development] == [f"E{index:02d}" for index in range(1, 9)]
    assert [case["case_id"] for case in holdout] == [f"H{index:02d}" for index in range(1, 5)]
    assert [case["case_id"] for case in teacher["tests"]] == ["T01", "T02", "T03"]
    assert teacher["excluded_from_learner_denominator"] is True


def test_baseline_arithmetic_and_holdout_truth_are_exact() -> None:
    development = {case["case_id"]: case for case in load("cases/development.json")["cases"]}
    assert "8 units" in development["E01"]["input"]
    assert "3 units" in development["E01"]["input"]
    assert "14 units" in development["E01"]["input"]
    assert "exactly 5" in development["E01"]["expected_criteria"][0]
    assert "exactly 9" in development["E01"]["expected_criteria"][1]

    answers = {item["case_id"]: item for item in load("teacher/holdout-answers.json")["answers"]}
    assertions = " ".join(answers["H01"]["expected_assertions"])
    assert "exactly 8" in assertions
    assert "exactly 11" in assertions


def test_source_authority_and_unknown_facts_are_explicit() -> None:
    old = load("sources/stock-exception-policy-v1.json")
    current = load("sources/stock-exception-policy-v2.json")
    calendar = load("sources/delivery-calendar.json")
    assert old["status"] == "superseded"
    assert old["superseded_by"] == current["source_id"]
    assert current["status"] == "current"
    assert current["effective_from"] > old["effective_to"]
    assert any("not present" in value for value in calendar["limitations"])


def test_restricted_marker_is_excluded_from_ordinary_learner_material() -> None:
    manifest = load("manifest.json")
    restricted = load("teacher/sources/restricted-operations-note.json")
    marker = restricted["authorization_marker"]
    assert restricted["source_id"] not in manifest["ordinary_learner_sources"]
    for relative in ("cases/development.json", "cases/holdout.json", "rubric.json"):
        assert marker not in (FIXTURE_ROOT / relative).read_text(encoding="utf-8")
    assert not (FIXTURE_ROOT / "sources" / "restricted-operations-note.json").exists()
    assert "answer_location" not in load("cases/holdout.json")
    assert "teacher" not in json.dumps(load("cases/holdout.json")).lower()


def test_pack_contains_no_clinical_or_real_data_claim() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in FIXTURE_ROOT.rglob("*.json")
    ).lower()
    assert "synthetic" in text
    assert "no real inventory" in text
    assert "patient name" not in text
    assert "prescription id" not in text
    assert "@example.com" not in text


def test_rubric_refuses_missing_evidence_and_keeps_authorization_separate() -> None:
    rubric = load("rubric.json")
    assert rubric["sets"]["development"] == {"attempted": 8, "minimum_complete_case_passes": 7}
    assert rubric["sets"]["holdout"] == {"attempted": 4, "minimum_complete_case_passes": 3}
    assert rubric["authorization_gate"]["separate"] is True
    assert rubric["authorization_gate"]["learner_score_cannot_satisfy"] is True
    assert any("missing" in condition.lower() for condition in rubric["insufficient_evidence_conditions"])
