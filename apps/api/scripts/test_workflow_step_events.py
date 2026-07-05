import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.crm_hygiene import CRMHygieneRequest  # noqa: E402
from app.models.follow_up import FollowUpDraftRequest  # noqa: E402
from app.models.lead_scoring import LeadScoringRequest  # noqa: E402
from app.models.meeting_summary import MeetingSummaryRequest  # noqa: E402
from app.models.proposal import ProposalDraftRequest  # noqa: E402
from app.models.review_queue import ReviewDecisionRequest, ReviewItemCreate  # noqa: E402
from app.services.crm_hygiene import check_crm_hygiene  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.follow_up import draft_follow_up  # noqa: E402
from app.services.lead_scoring import score_lead  # noqa: E402
from app.services.meeting_summary import summarize_meeting  # noqa: E402
from app.services.proposal import draft_proposal  # noqa: E402
from app.services.review_queue import (  # noqa: E402
    approve_review_item,
    create_review_item,
    reject_review_item,
)
from app.services.workflow_logs import list_workflow_runs, reset_workflow_runs  # noqa: E402
from app.services.workflow_steps import (  # noqa: E402
    list_step_events,
    list_step_events_by_workflow_run_id,
    log_step_started,
    log_step_success,
)


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    reset_persistence_tables()
    reset_workflow_runs()

    checks = [
        ("step event can be created and listed", check_step_event_foundation),
        ("lead scoring creates required step events", check_lead_scoring_steps),
        ("meeting summary creates required step events", check_meeting_summary_steps),
        ("follow-up drafting creates required step events", check_follow_up_steps),
        ("proposal drafting creates required step events", check_proposal_steps),
        ("CRM hygiene creates required step events", check_crm_hygiene_steps),
        ("review decisions create operational step events", check_review_decision_steps),
    ]

    passed = 0
    failed = 0
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


def check_step_event_foundation() -> None:
    reset_persistence_tables()
    reset_workflow_runs()
    started = log_step_started(
        "workflow_run_step_test",
        "manual_step_test",
        "workflow_started",
        1,
        "test_entity",
        "entity_001",
    )
    success = log_step_success(
        "workflow_run_step_test",
        "manual_step_test",
        "workflow_completed",
        2,
        "test_entity",
        "entity_001",
    )

    assert started is not None
    assert success is not None
    all_events = list_step_events()
    run_events = list_step_events_by_workflow_run_id("workflow_run_step_test")

    assert len(all_events) == 2
    assert len(run_events) == 2
    assert all(event.workflow_run_id for event in run_events)
    assert all(event.workflow_name for event in run_events)
    assert all(event.step_name for event in run_events)
    assert all(event.step_status for event in run_events)
    assert all(event.created_at for event in run_events)


def check_lead_scoring_steps() -> None:
    reset_persistence_tables()
    reset_workflow_runs()
    lead = load_json(REPO_ROOT / "sample-data" / "leads.json")[0]
    score_lead(LeadScoringRequest(**lead))
    assert_steps(
        "lead_scoring_routing",
        [
            "workflow_started",
            "input_validated",
            "lead_scored",
            "route_recommended",
            "review_requirement_evaluated",
            "audit_events_written",
            "workflow_completed",
        ],
    )


def check_meeting_summary_steps() -> None:
    reset_persistence_tables()
    reset_workflow_runs()
    meeting = load_json(REPO_ROOT / "sample-data" / "meeting-transcripts.json")[2]
    summarize_meeting(MeetingSummaryRequest(**meeting))
    assert_steps(
        "meeting_capture_crm_summary",
        [
            "workflow_started",
            "input_validated",
            "meeting_summary_created",
            "next_steps_extracted",
            "recommended_actions_created",
            "review_actions_identified",
            "audit_events_written",
            "workflow_completed",
        ],
    )


def check_follow_up_steps() -> None:
    reset_persistence_tables()
    reset_workflow_runs()
    follow_up = load_json(REPO_ROOT / "sample-data" / "follow-up-inputs.json")[0]
    draft_follow_up(FollowUpDraftRequest(**follow_up))
    assert_steps(
        "follow_up_drafting",
        [
            "workflow_started",
            "input_validated",
            "follow_up_context_loaded",
            "follow_up_draft_created",
            "guardrails_applied",
            "review_item_created",
            "audit_events_written",
            "workflow_completed",
        ],
    )


def check_proposal_steps() -> None:
    reset_persistence_tables()
    reset_workflow_runs()
    proposal = load_json(REPO_ROOT / "sample-data" / "proposal-inputs.json")[0]
    draft_proposal(ProposalDraftRequest(**proposal))
    assert_steps(
        "proposal_outline_drafting",
        [
            "workflow_started",
            "input_validated",
            "proposal_context_loaded",
            "proposal_outline_created",
            "risk_notes_created",
            "guardrails_applied",
            "review_item_created",
            "audit_events_written",
            "workflow_completed",
        ],
    )


def check_crm_hygiene_steps() -> None:
    reset_persistence_tables()
    reset_workflow_runs()
    records = load_json(REPO_ROOT / "sample-data" / "crm-hygiene-inputs.json")

    check_crm_hygiene(CRMHygieneRequest(**records[0]))
    clean_events = events_for_last_run("crm_hygiene_deal_risk_monitor")
    clean_review_step = find_step(clean_events, "review_item_created_if_required")
    assert clean_review_step.step_status == "skipped"

    check_crm_hygiene(CRMHygieneRequest(**records[5]))
    risky_events = events_for_last_run("crm_hygiene_deal_risk_monitor")
    risky_review_step = find_step(risky_events, "review_item_created_if_required")
    assert risky_review_step.step_status == "success"
    assert_step_names(
        risky_events,
        [
            "workflow_started",
            "input_validated",
            "crm_record_checked",
            "missing_fields_checked",
            "stale_activity_checked",
            "risk_level_assigned",
            "review_item_created_if_required",
            "audit_events_written",
            "workflow_completed",
        ],
    )


def check_review_decision_steps() -> None:
    reset_persistence_tables()
    reset_workflow_runs()

    approve_item = create_review_item(sample_review_item("review_approve"))
    approve_review_item(
        approve_item.review_item_id,
        ReviewDecisionRequest(
            actor="sales_manager",
            decision_reason="Approved for test.",
        ),
    )
    approve_events = list_step_events_by_workflow_run_id(approve_item.workflow_run_id)
    assert_step_names(approve_events, review_decision_step_names())

    reject_item = create_review_item(sample_review_item("review_reject"))
    reject_review_item(
        reject_item.review_item_id,
        ReviewDecisionRequest(
            actor="sales_manager",
            decision_reason="Rejected for test.",
        ),
    )
    reject_events = list_step_events_by_workflow_run_id(reject_item.workflow_run_id)
    assert_step_names(reject_events, review_decision_step_names())


def sample_review_item(entity_id: str) -> ReviewItemCreate:
    return ReviewItemCreate(
        workflow_run_id=f"workflow_run_{entity_id}",
        workflow_name="follow_up_drafting",
        entity_type="follow_up",
        entity_id=entity_id,
        company="Northstar Analytics",
        contact_name="Maya Chen",
        review_type="follow_up_draft",
        title="Review follow-up draft",
        priority="high",
        risk_level="medium",
        review_reasons=["Customer-facing draft requires sales rep review."],
        proposed_action="Review and approve the follow-up draft.",
        proposed_output="Draft follow-up body.",
    )


def review_decision_step_names() -> list[str]:
    return [
        "review_decision_started",
        "review_item_loaded",
        "review_item_status_updated",
        "audit_event_written",
        "review_decision_completed",
    ]


def assert_steps(workflow_name: str, expected_steps: list[str]) -> None:
    events = events_for_last_run(workflow_name)
    assert_step_names(events, expected_steps)
    assert find_step(events, "workflow_completed").step_status == "success"


def events_for_last_run(workflow_name: str):
    run = next(
        run
        for run in reversed(list_workflow_runs())
        if run.workflow_name == workflow_name
    )
    return list_step_events_by_workflow_run_id(run.workflow_run_id)


def assert_step_names(events, expected_steps: list[str]) -> None:
    names = [event.step_name for event in events]
    for expected_step in expected_steps:
        assert expected_step in names, f"missing step {expected_step}; got {names}"
    assert all(event.workflow_run_id for event in events)
    assert all(event.workflow_name for event in events)
    assert all(event.step_name for event in events)
    assert all(event.step_status for event in events)
    assert all(event.created_at for event in events)


def find_step(events, step_name: str):
    return next(event for event in events if event.step_name == step_name)


if __name__ == "__main__":
    raise SystemExit(main())
