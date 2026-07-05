import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.follow_up import FollowUpDraftRequest  # noqa: E402
from app.services.follow_up import WORKFLOW_NAME, draft_follow_up  # noqa: E402
from app.services.workflow_logs import (  # noqa: E402
    get_workflow_metrics,
    list_workflow_runs,
    reset_workflow_runs,
)


BANNED_PROMISE_LANGUAGE = [
    "we guarantee",
    "guaranteed",
    "no risk",
    "fully secure",
    "legally approved",
    "will definitely",
    "instant implementation",
]


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    reset_workflow_runs()
    inputs = load_json(REPO_ROOT / "sample-data" / "follow-up-inputs.json")
    expected_results = load_json(
        REPO_ROOT / "sample-data" / "follow-up-expected-results.json"
    )
    expected_by_id = {result["follow_up_id"]: result for result in expected_results}

    passed = 0
    failed = 0

    for input_data in inputs:
        request = FollowUpDraftRequest(**input_data)
        result = draft_follow_up(request)
        expected = expected_by_id[result.follow_up_id]
        failures = checked_field_failures(result, expected)

        if failures:
            failed += 1
            print(f"FAIL {result.follow_up_id}:")
            for failure in failures:
                print(f"  - {failure}")
        else:
            passed += 1
            print(
                f"PASS {result.follow_up_id}: "
                f"confidence={result.confidence}, "
                f"recommended_send_timing={result.recommended_send_timing}, "
                f"review_required={result.review_required}"
            )

    log_failures = observability_failures(expected_count=len(inputs))
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

    if result.review_required is not True:
        failures.append("review_required: expected True")

    if result.confidence != expected["confidence"]:
        failures.append(
            f"confidence: expected {expected['confidence']!r}, got {result.confidence!r}"
        )

    if result.recommended_send_timing != expected["recommended_send_timing"]:
        failures.append(
            "recommended_send_timing: "
            f"expected {expected['recommended_send_timing']!r}, "
            f"got {result.recommended_send_timing!r}"
        )

    for reason in expected["required_review_reasons"]:
        if reason not in result.review_reasons:
            failures.append(f"review_reasons: missing {reason!r}")

    if not result.draft_body.strip():
        failures.append("draft_body: expected non-empty draft body")

    draft_body_lower = result.draft_body.lower()
    for banned_phrase in BANNED_PROMISE_LANGUAGE:
        if banned_phrase in draft_body_lower:
            failures.append(f"draft_body: contains banned phrase {banned_phrase!r}")

    return failures


def observability_failures(expected_count: int) -> list[str]:
    failures: list[str] = []
    runs = list_workflow_runs()
    metrics = get_workflow_metrics()

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

    if metrics.human_review_required_count != expected_count:
        failures.append(
            "metrics.human_review_required_count: "
            f"expected {expected_count}, got {metrics.human_review_required_count}"
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
        if run.human_review_required is not True:
            failures.append("human_review_required: expected True")
        if not run.next_action:
            failures.append("next_action: expected non-empty next action")

    return failures


if __name__ == "__main__":
    raise SystemExit(main())
