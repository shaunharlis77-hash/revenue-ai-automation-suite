import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.review_queue import ReviewDecisionRequest, ReviewItemCreate  # noqa: E402
from app.services.audit_trail import list_audit_events  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.review_queue import (  # noqa: E402
    approve_review_item,
    create_review_item,
    get_review_item,
    list_review_items,
    reject_review_item,
)


def main() -> int:
    reset_persistence_tables()
    passed = 0
    failed = 0

    checks = [
        ("review item can be created and retrieved", check_create_and_get_item),
        ("review item can be approved with audit event", check_approve_item),
        ("review item can be rejected with audit event", check_reject_item),
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


def sample_review_item(entity_id: str = "follow_up_001") -> ReviewItemCreate:
    return ReviewItemCreate(
        workflow_run_id="workflow_run_001",
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
        assigned_to="Alex Rivera",
        metadata_json={"test_case": "review_queue"},
    )


def check_create_and_get_item() -> None:
    item = create_review_item(sample_review_item())
    items = list_review_items()
    fetched = get_review_item(item.review_item_id)

    assert item.review_item_id
    assert len(items) == 1
    assert fetched.review_item_id == item.review_item_id
    assert fetched.status == "pending"
    assert fetched.review_type == "follow_up_draft"
    assert fetched.metadata_json["test_case"] == "review_queue"


def check_approve_item() -> None:
    item = create_review_item(sample_review_item("follow_up_approve"))
    approved = approve_review_item(
        item.review_item_id,
        ReviewDecisionRequest(
            actor="sales_manager",
            decision_reason="Draft is accurate and ready for rep use.",
        ),
    )
    events = list_audit_events()
    approval_events = [
        event
        for event in events
        if event.event_type == "review_approved"
        and event.output_reference == item.review_item_id
    ]

    assert approved.status == "approved"
    assert approved.decision == "approved"
    assert approved.decision_reason == "Draft is accurate and ready for rep use."
    assert len(approval_events) == 1
    assert approval_events[0].actor == "sales_manager"


def check_reject_item() -> None:
    item = create_review_item(sample_review_item("follow_up_reject"))
    rejected = reject_review_item(
        item.review_item_id,
        ReviewDecisionRequest(
            actor="sales_manager",
            decision_reason="Draft needs corrected next-step language.",
        ),
    )
    events = list_audit_events()
    rejection_events = [
        event
        for event in events
        if event.event_type == "review_rejected"
        and event.output_reference == item.review_item_id
    ]

    assert rejected.status == "rejected"
    assert rejected.decision == "rejected"
    assert rejected.decision_reason == "Draft needs corrected next-step language."
    assert len(rejection_events) == 1
    assert rejection_events[0].actor == "sales_manager"


if __name__ == "__main__":
    raise SystemExit(main())
