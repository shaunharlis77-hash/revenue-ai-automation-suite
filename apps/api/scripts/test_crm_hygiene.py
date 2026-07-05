import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.crm_hygiene import CRMHygieneRequest  # noqa: E402
from app.services.crm_hygiene import WORKFLOW_NAME, check_crm_hygiene  # noqa: E402
from app.services.workflow_logs import (  # noqa: E402
    get_workflow_metrics,
    list_workflow_runs,
    reset_workflow_runs,
)


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    reset_workflow_runs()
    inputs = load_json(REPO_ROOT / "sample-data" / "crm-hygiene-inputs.json")
    expected_results = load_json(
        REPO_ROOT / "sample-data" / "crm-hygiene-expected-results.json"
    )
    expected_by_id = {result["record_id"]: result for result in expected_results}

    passed = 0
    failed = 0

    for input_data in inputs:
        request = CRMHygieneRequest(**input_data)
        result = check_crm_hygiene(request)
        expected = expected_by_id[result.record_id]
        failures = checked_field_failures(result, expected)

        if failures:
            failed += 1
            print(f"FAIL {result.record_id}:")
            for failure in failures:
                print(f"  - {failure}")
        else:
            passed += 1
            print(
                f"PASS {result.record_id}: "
                f"score={result.hygiene_score}, "
                f"risk_level={result.risk_level}, "
                f"human_review_required={result.human_review_required}"
            )

    log_failures = observability_failures(expected_results)
    if log_failures:
        failed += 1
        print("FAIL observability:")
        for failure in log_failures:
            print(f"  - {failure}")
    else:
        passed += 1
        print("PASS observability: workflow logs created")

    print(f"Summary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def checked_field_failures(result, expected: dict) -> list[str]:
    failures: list[str] = []

    if result.hygiene_score != expected["hygiene_score"]:
        failures.append(
            f"hygiene_score: expected {expected['hygiene_score']}, got {result.hygiene_score}"
        )

    if result.risk_level != expected["risk_level"]:
        failures.append(
            f"risk_level: expected {expected['risk_level']!r}, got {result.risk_level!r}"
        )

    if result.human_review_required != expected["human_review_required"]:
        failures.append(
            "human_review_required: "
            f"expected {expected['human_review_required']}, got {result.human_review_required}"
        )

    if result.missing_fields != expected["missing_fields"]:
        failures.append(
            f"missing_fields: expected {expected['missing_fields']!r}, got {result.missing_fields!r}"
        )

    if expected["recommended_actions_required"] and not result.recommended_actions:
        failures.append("recommended_actions: expected at least one action")

    if result.record_id == "crm_001":
        if result.risk_level != "low" or result.hygiene_score < 90:
            failures.append("clean case should have low risk and high hygiene score")

    if result.record_id == "crm_006":
        if result.risk_level != "critical" or result.hygiene_score > 35:
            failures.append("critical case should have critical risk and low hygiene score")

    return failures


def observability_failures(expected_results: list[dict]) -> list[str]:
    failures: list[str] = []
    runs = list_workflow_runs()
    metrics = get_workflow_metrics()
    expected_count = len(expected_results)
    expected_review_count = sum(
        1 for result in expected_results if result["human_review_required"]
    )

    if len(runs) != expected_count:
        failures.append(f"workflow logs: expected {expected_count}, got {len(runs)}")
    if metrics.total_workflow_runs != expected_count:
        failures.append(
            "metrics.total_workflow_runs: "
            f"expected {expected_count}, got {metrics.total_workflow_runs}"
        )
    if metrics.successful_runs != expected_count:
        failures.append(
            f"metrics.successful_runs: expected {expected_count}, got {metrics.successful_runs}"
        )
    if metrics.failed_runs != 0:
        failures.append(f"metrics.failed_runs: expected 0, got {metrics.failed_runs}")
    if metrics.human_review_required_count != expected_review_count:
        failures.append(
            "metrics.human_review_required_count: "
            f"expected {expected_review_count}, got {metrics.human_review_required_count}"
        )
    if metrics.runs_by_workflow_name.get(WORKFLOW_NAME) != expected_count:
        failures.append(
            "metrics.runs_by_workflow_name: "
            f"expected {WORKFLOW_NAME}={expected_count}, "
            f"got {metrics.runs_by_workflow_name.get(WORKFLOW_NAME)}"
        )

    for run in runs:
        if run.workflow_name != WORKFLOW_NAME:
            failures.append(f"workflow_name: expected {WORKFLOW_NAME}, got {run.workflow_name}")
        if run.status != "success":
            failures.append(f"status: expected success, got {run.status}")
        if not run.output_summary:
            failures.append("output_summary: expected non-empty summary")
        if not run.next_action:
            failures.append("next_action: expected non-empty next action")

    return failures


if __name__ == "__main__":
    raise SystemExit(main())
