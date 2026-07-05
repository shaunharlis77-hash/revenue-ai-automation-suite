import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.audit import AuditEventCreate  # noqa: E402
from app.services import audit_trail  # noqa: E402
from app.services.audit_trail import (  # noqa: E402
    create_audit_event,
    get_audit_event,
    list_audit_events,
)
from app.services.database import reset_persistence_tables  # noqa: E402


def main() -> int:
    reset_persistence_tables()
    passed = 0
    failed = 0

    checks = [
        ("audit event can be created", check_create_event),
        ("audit events can be listed and retrieved", check_list_and_get_event),
        ("audit events are append-only by design", check_append_only_design),
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


def sample_event(entity_id: str = "lead_001") -> AuditEventCreate:
    return AuditEventCreate(
        workflow_run_id="workflow_run_001",
        workflow_name="lead_scoring_routing",
        entity_type="lead",
        entity_id=entity_id,
        event_type="workflow_completed",
        event_source="test",
        actor="test_runner",
        input_reference=entity_id,
        output_reference=f"output_{entity_id}",
        guardrails_triggered=["human_review_required"],
        human_review_required=True,
        decision="logged",
        decision_reason="Test event was created.",
        metadata_json={"test_case": "audit_trail"},
    )


def check_create_event() -> None:
    event = create_audit_event(sample_event())

    assert event.event_id
    assert event.workflow_name == "lead_scoring_routing"
    assert event.event_type == "workflow_completed"
    assert event.actor == "test_runner"
    assert event.entity_type == "lead"
    assert event.entity_id == "lead_001"
    assert event.metadata_json["test_case"] == "audit_trail"


def check_list_and_get_event() -> None:
    event = create_audit_event(sample_event("lead_002"))
    events = list_audit_events()
    fetched = get_audit_event(event.event_id)

    assert len(events) == 2
    assert fetched.event_id == event.event_id
    assert fetched.entity_id == "lead_002"
    assert fetched.guardrails_triggered == ["human_review_required"]


def check_append_only_design() -> None:
    before = len(list_audit_events())
    create_audit_event(sample_event("lead_003"))
    after = len(list_audit_events())

    assert after == before + 1
    assert not hasattr(audit_trail, "delete_audit_event")
    assert not hasattr(audit_trail, "update_audit_event")


if __name__ == "__main__":
    raise SystemExit(main())
