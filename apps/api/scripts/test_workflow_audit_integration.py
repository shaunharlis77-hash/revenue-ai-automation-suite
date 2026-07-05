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
from app.services.audit_trail import list_audit_events  # noqa: E402
from app.services.crm_hygiene import check_crm_hygiene  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.follow_up import draft_follow_up  # noqa: E402
from app.services.lead_scoring import score_lead  # noqa: E402
from app.services.meeting_summary import summarize_meeting  # noqa: E402
from app.services.proposal import draft_proposal  # noqa: E402
from app.services.review_queue import list_review_items  # noqa: E402
from app.services.workflow_logs import reset_workflow_runs  # noqa: E402


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    reset_workflow_runs()
    reset_persistence_tables()

    passed = 0
    failed = 0

    checks = [
        ("lead scoring creates audit events", check_lead_scoring_audit),
        ("meeting summary creates audit events", check_meeting_summary_audit),
        ("follow-up drafting creates review item and audit events", check_follow_up_audit),
        ("proposal drafting creates review item and audit events", check_proposal_audit),
        ("CRM hygiene creates review item and audit events", check_crm_hygiene_audit),
        ("guardrail-triggered events exist", check_guardrail_events),
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


def check_lead_scoring_audit() -> None:
    lead_data = load_json(REPO_ROOT / "sample-data" / "leads.json")[0]
    result = score_lead(LeadScoringRequest(**lead_data))
    events = workflow_events("lead_scoring_routing")

    assert result.human_review_required is True
    assert has_event(events, "workflow_started")
    assert has_event(events, "lead_scored")
    assert has_event(events, "guardrail_triggered")
    assert has_event(events, "crm_update_recommended")
    assert has_event(events, "workflow_completed")


def check_meeting_summary_audit() -> None:
    meeting_data = load_json(REPO_ROOT / "sample-data" / "meeting-transcripts.json")[2]
    result = summarize_meeting(MeetingSummaryRequest(**meeting_data))
    events = workflow_events("meeting_capture_crm_summary")
    review_items = workflow_review_items("meeting_capture_crm_summary")

    assert result.human_review_required is True
    assert has_event(events, "workflow_started")
    assert has_event(events, "meeting_summary_created")
    assert has_event(events, "next_steps_extracted")
    assert has_event(events, "guardrail_triggered")
    assert has_event(events, "crm_update_recommended")
    assert has_event(events, "workflow_completed")
    assert review_items


def check_follow_up_audit() -> None:
    follow_up_data = load_json(REPO_ROOT / "sample-data" / "follow-up-inputs.json")[0]
    result = draft_follow_up(FollowUpDraftRequest(**follow_up_data))
    events = workflow_events("follow_up_drafting")
    review_items = workflow_review_items("follow_up_drafting")

    assert result.review_required is True
    assert has_event(events, "workflow_started")
    assert has_event(events, "follow_up_draft_created")
    assert has_event(events, "guardrail_triggered")
    assert has_event(events, "review_created")
    assert has_event(events, "workflow_completed")
    assert any(item.review_type == "follow_up_draft" for item in review_items)


def check_proposal_audit() -> None:
    proposal_data = load_json(REPO_ROOT / "sample-data" / "proposal-inputs.json")[2]
    result = draft_proposal(ProposalDraftRequest(**proposal_data))
    events = workflow_events("proposal_outline_drafting")
    review_items = workflow_review_items("proposal_outline_drafting")

    assert result.human_review_required is True
    assert has_event(events, "workflow_started")
    assert has_event(events, "proposal_outline_created")
    assert has_event(events, "guardrail_triggered")
    assert has_event(events, "review_created")
    assert has_event(events, "workflow_completed")
    assert any(item.review_type == "proposal_outline" for item in review_items)


def check_crm_hygiene_audit() -> None:
    hygiene_data = load_json(REPO_ROOT / "sample-data" / "crm-hygiene-inputs.json")[5]
    result = check_crm_hygiene(CRMHygieneRequest(**hygiene_data))
    events = workflow_events("crm_hygiene_deal_risk_monitor")
    review_items = workflow_review_items("crm_hygiene_deal_risk_monitor")

    assert result.risk_level == "critical"
    assert result.human_review_required is True
    assert has_event(events, "workflow_started")
    assert has_event(events, "crm_hygiene_checked")
    assert has_event(events, "guardrail_triggered")
    assert has_event(events, "review_created")
    assert has_event(events, "workflow_completed")
    assert any(item.review_type == "high_risk_deal" for item in review_items)


def check_guardrail_events() -> None:
    guardrail_events = [
        event for event in list_audit_events() if event.event_type == "guardrail_triggered"
    ]
    review_items = list_review_items()

    assert len(guardrail_events) >= 5
    assert all(event.guardrails_triggered for event in guardrail_events)
    assert review_items


def workflow_events(workflow_name: str):
    return [event for event in list_audit_events() if event.workflow_name == workflow_name]


def workflow_review_items(workflow_name: str):
    return [item for item in list_review_items() if item.workflow_name == workflow_name]


def has_event(events, event_type: str) -> bool:
    return any(event.event_type == event_type for event in events)


if __name__ == "__main__":
    raise SystemExit(main())
