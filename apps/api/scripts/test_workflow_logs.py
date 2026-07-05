import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.lead_scoring import LeadScoringRequest  # noqa: E402
from app.models.meeting_summary import MeetingSummaryRequest  # noqa: E402
from app.models.workflow_logs import (  # noqa: E402
    WorkflowRunFailureRequest,
    WorkflowRunStartRequest,
    WorkflowRunSuccessRequest,
)
from app.services.lead_scoring import WORKFLOW_NAME as LEAD_WORKFLOW_NAME  # noqa: E402
from app.services.lead_scoring import score_lead  # noqa: E402
from app.services.meeting_summary import WORKFLOW_NAME as MEETING_WORKFLOW_NAME  # noqa: E402
from app.services.meeting_summary import summarize_meeting  # noqa: E402
from app.services.workflow_logs import (  # noqa: E402
    get_recent_workflow_runs,
    get_workflow_metrics,
    list_workflow_runs,
    mark_workflow_failure,
    mark_workflow_success,
    reset_workflow_runs,
    start_workflow_run,
)


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    passed = 0
    failed = 0

    checks = [
        ("manual start/success/failure logging", check_manual_logging),
        ("workflow services create success logs", check_workflow_service_logging),
    ]

    for name, check in checks:
        try:
            check()
            passed += 1
            print(f"PASS {name}")
        except AssertionError as error:
            failed += 1
            print(f"FAIL {name}: {error}")

    print(f"Summary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def check_manual_logging() -> None:
    reset_workflow_runs()

    started = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="manual_test_workflow",
            input_reference="manual_001",
        )
    )
    assert started.status == "started"
    assert started.workflow_run_id
    assert started.started_at
    assert started.created_at

    success = mark_workflow_success(
        started.workflow_run_id,
        WorkflowRunSuccessRequest(
            output_summary="Manual test completed.",
            human_review_required=False,
            next_action="No action needed.",
        ),
    )
    assert success.status == "success"
    assert success.completed_at
    assert success.output_summary == "Manual test completed."

    failed_run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="manual_test_workflow",
            input_reference="manual_002",
        )
    )
    failure = mark_workflow_failure(
        failed_run.workflow_run_id,
        WorkflowRunFailureRequest(
            failure_step="manual_step",
            failure_reason="Manual failure test.",
            input_reference="manual_002",
        ),
    )
    assert failure.status == "failed"
    assert failure.failed_at
    assert failure.failure_step == "manual_step"
    assert failure.human_review_required is True

    metrics = get_workflow_metrics()
    assert metrics.total_workflow_runs == 2
    assert metrics.successful_runs == 1
    assert metrics.failed_runs == 1
    assert metrics.human_review_required_count == 1
    assert metrics.runs_by_workflow_name == {"manual_test_workflow": 2}
    assert len(metrics.recent_failures) == 1
    assert get_recent_workflow_runs()[0].workflow_run_id == failed_run.workflow_run_id


def check_workflow_service_logging() -> None:
    reset_workflow_runs()

    lead_data = load_json(REPO_ROOT / "sample-data" / "leads.json")[0]
    meeting_data = load_json(REPO_ROOT / "sample-data" / "meeting-transcripts.json")[0]

    lead_result = score_lead(LeadScoringRequest(**lead_data))
    meeting_result = summarize_meeting(MeetingSummaryRequest(**meeting_data))

    runs = list_workflow_runs()
    metrics = get_workflow_metrics()

    assert len(runs) == 2
    assert metrics.total_workflow_runs == 2
    assert metrics.successful_runs == 2
    assert metrics.failed_runs == 0
    assert metrics.runs_by_workflow_name[LEAD_WORKFLOW_NAME] == 1
    assert metrics.runs_by_workflow_name[MEETING_WORKFLOW_NAME] == 1

    lead_run = next(run for run in runs if run.workflow_name == LEAD_WORKFLOW_NAME)
    meeting_run = next(run for run in runs if run.workflow_name == MEETING_WORKFLOW_NAME)

    assert lead_run.input_reference == lead_result.lead_id
    assert str(lead_result.lead_score) in lead_run.output_summary
    assert lead_run.human_review_required == lead_result.human_review_required
    assert lead_run.next_action == lead_result.next_best_action

    assert meeting_run.input_reference == meeting_result.meeting_id
    assert meeting_result.confidence in meeting_run.output_summary
    assert meeting_run.human_review_required == meeting_result.human_review_required
    assert meeting_run.next_action


if __name__ == "__main__":
    raise SystemExit(main())
