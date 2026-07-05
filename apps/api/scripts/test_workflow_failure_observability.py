import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.workflow_logs import WorkflowRunFailureRequest, WorkflowRunStartRequest  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.workflow_logs import (  # noqa: E402
    list_workflow_runs,
    mark_workflow_failure,
    reset_workflow_runs,
    start_workflow_run,
)
from app.services.workflow_steps import (  # noqa: E402
    list_step_events_by_workflow_run_id,
    log_step_failure,
    log_step_started,
)


def main() -> int:
    reset_persistence_tables()
    reset_workflow_runs()

    checks = [
        ("failed step event captures diagnostic details", check_failed_step_event),
        ("workflow run records failed step", check_workflow_run_failure_step),
        ("audit write failure is visible as operational failure", check_audit_write_failure_visibility),
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


def check_failed_step_event() -> None:
    run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="failure_observability_test",
            input_reference="failure_001",
        )
    )
    log_step_started(
        run.workflow_run_id,
        run.workflow_name,
        "workflow_started",
        1,
        "test_entity",
        "failure_001",
    )
    try:
        raise RuntimeError("Simulated scoring failure.")
    except RuntimeError as error:
        log_step_failure(
            run.workflow_run_id,
            run.workflow_name,
            "lead_scored",
            error,
            2,
            "test_entity",
            "failure_001",
            failure_reason="The deterministic scoring step raised an exception.",
            retryable=False,
            recommended_fix="Check the lead scoring inputs and deterministic scoring rules.",
        )
        mark_workflow_failure(
            run.workflow_run_id,
            WorkflowRunFailureRequest(
                failure_step="lead_scored",
                failure_reason=str(error),
                input_reference="failure_001",
            ),
        )

    failed_step = next(
        event
        for event in list_step_events_by_workflow_run_id(run.workflow_run_id)
        if event.step_name == "lead_scored" and event.step_status == "failed"
    )

    assert failed_step.error_type == "RuntimeError"
    assert failed_step.error_message == "Simulated scoring failure."
    assert failed_step.failure_reason == "The deterministic scoring step raised an exception."
    assert failed_step.recommended_fix == "Check the lead scoring inputs and deterministic scoring rules."
    assert failed_step.retryable is False


def check_workflow_run_failure_step() -> None:
    failed_run = next(
        run
        for run in list_workflow_runs()
        if run.workflow_name == "failure_observability_test"
    )
    assert failed_run.status == "failed"
    assert failed_run.failure_step == "lead_scored"
    assert failed_run.failure_reason == "Simulated scoring failure."


def check_audit_write_failure_visibility() -> None:
    run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="audit_write_failure_test",
            input_reference="audit_failure_001",
        )
    )
    log_step_failure(
        run.workflow_run_id,
        run.workflow_name,
        "audit_events_written",
        RuntimeError("Simulated audit persistence failure."),
        5,
        "test_entity",
        "audit_failure_001",
        failure_reason="Audit event write failed after workflow output was created.",
        retryable=True,
        recommended_fix="Check database availability and retry the audit write.",
    )
    mark_workflow_failure(
        run.workflow_run_id,
        WorkflowRunFailureRequest(
            failure_step="audit_events_written",
            failure_reason="Simulated audit persistence failure.",
            input_reference="audit_failure_001",
        ),
    )

    failed_step = next(
        event
        for event in list_step_events_by_workflow_run_id(run.workflow_run_id)
        if event.step_name == "audit_events_written" and event.step_status == "failed"
    )
    failed_run = next(
        item
        for item in list_workflow_runs()
        if item.workflow_run_id == run.workflow_run_id
    )

    assert failed_step.retryable is True
    assert failed_step.error_type == "RuntimeError"
    assert failed_step.recommended_fix == "Check database availability and retry the audit write."
    assert failed_run.failure_step == "audit_events_written"


if __name__ == "__main__":
    raise SystemExit(main())
