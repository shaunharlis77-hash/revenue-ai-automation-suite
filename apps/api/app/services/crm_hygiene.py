"""Deterministic Workflow 5: CRM Hygiene / Deal Risk Monitor.

This service checks CRM-style records for missing information and deal risk. It
does not update CRM data or call external systems.
"""

from datetime import date

from app.models.crm_hygiene import CRMHygieneRequest, CRMHygieneResponse
from app.models.workflow_logs import (
    WorkflowRunFailureRequest,
    WorkflowRunStartRequest,
    WorkflowRunSuccessRequest,
)
from app.services.workflow_logs import (
    mark_workflow_failure,
    mark_workflow_success,
    start_workflow_run,
)
from app.services.workflow_steps import (
    log_step_failure,
    log_step_skipped,
    log_step_started,
    log_step_success,
)
from app.services.workflow_audit import (
    audit_completed,
    audit_started,
    audit_workflow_failure,
    record_crm_hygiene_audit,
)


WORKFLOW_NAME = "crm_hygiene_deal_risk_monitor"
REFERENCE_DATE = date(2026, 7, 3)
MISSING_VALUES = {"", "unknown", "none", "not_set", "n/a", "na", "unclear"}
STALE_ACTIVITY_DAYS = 21
LONG_STAGE_DAYS = 30
VERY_LONG_STAGE_DAYS = 45


def check_crm_hygiene(request: CRMHygieneRequest) -> CRMHygieneResponse:
    workflow_run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name=WORKFLOW_NAME,
            input_reference=request.record_id,
        )
    )
    failed_step = "workflow_started"
    log_step_started(
        workflow_run.workflow_run_id,
        WORKFLOW_NAME,
        "workflow_started",
        1,
        "crm_record",
        request.record_id,
    )

    try:
        audit_started(workflow_run, "crm_record", request.record_id)
        failed_step = "input_validated"
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "input_validated",
            2,
            "crm_record",
            request.record_id,
        )
        failed_step = "crm_record_checked"
        result = _check_crm_hygiene(request)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "crm_record_checked",
            3,
            "crm_record",
            request.record_id,
            {"hygiene_score": result.hygiene_score},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "missing_fields_checked",
            4,
            "crm_record",
            request.record_id,
            {"missing_fields": result.missing_fields},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "stale_activity_checked",
            5,
            "crm_record",
            request.record_id,
            {"stale_activity": result.stale_activity},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "risk_level_assigned",
            6,
            "crm_record",
            request.record_id,
            {"risk_level": result.risk_level},
        )
        failed_step = "audit_events_written"
        record_crm_hygiene_audit(workflow_run, request, result)
        if result.human_review_required:
            log_step_success(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "review_item_created_if_required",
                7,
                "crm_record",
                request.record_id,
                {"risk_level": result.risk_level},
            )
        else:
            log_step_skipped(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "review_item_created_if_required",
                "No review item required for low-risk CRM hygiene result.",
                7,
                "crm_record",
                request.record_id,
                {"risk_level": result.risk_level},
            )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "audit_events_written",
            8,
            "crm_record",
            request.record_id,
        )
        mark_workflow_success(
            workflow_run.workflow_run_id,
            WorkflowRunSuccessRequest(
                output_summary=(
                    f"CRM hygiene checked with {result.risk_level} risk "
                    f"and score {result.hygiene_score}."
                ),
                human_review_required=result.human_review_required,
                next_action=result.next_action,
            ),
        )
        audit_completed(
            workflow_run,
            "crm_record",
            request.record_id,
            result.record_id,
            result.human_review_required,
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "workflow_completed",
            9,
            "crm_record",
            request.record_id,
        )
        return result
    except Exception as error:
        log_step_failure(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            failed_step,
            error,
            entity_type="crm_record",
            entity_id=request.record_id,
            failure_reason=str(error),
            retryable=failed_step == "audit_events_written",
            recommended_fix="Check CRM hygiene input values and the audit/review persistence path.",
        )
        mark_workflow_failure(
            workflow_run.workflow_run_id,
            WorkflowRunFailureRequest(
                failure_step=failed_step,
                failure_reason=str(error),
                input_reference=request.record_id,
            ),
        )
        try:
            audit_workflow_failure(
                workflow_run,
                "crm_record",
                request.record_id,
                failed_step,
                str(error),
            )
        except Exception as audit_error:
            log_step_failure(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "audit_events_written",
                audit_error,
                entity_type="crm_record",
                entity_id=request.record_id,
                failure_reason="Audit write failed while recording workflow failure.",
                retryable=True,
                recommended_fix="Check audit event persistence after the CRM hygiene failure.",
                metadata_json={"original_failure_step": failed_step},
            )
        raise


def _check_crm_hygiene(request: CRMHygieneRequest) -> CRMHygieneResponse:
    issues: list[str] = []
    recommended_actions: list[str] = []
    missing_fields = detect_missing_fields(request)
    stale_activity = is_stale_activity(request.last_activity_date)
    score = 100
    major_issue_count = 0

    if is_missing(request.owner):
        score -= 20
        major_issue_count += 1
        issues.append("Owner is missing.")
        recommended_actions.append("Assign an owner before the deal is worked.")

    if is_missing(request.next_step):
        score -= 20
        major_issue_count += 1
        issues.append("Next step is missing or unclear.")
        recommended_actions.append("Add a clear next step with an owner and due date.")

    if stale_activity:
        score -= 18
        major_issue_count += 1
        issues.append("Last activity is stale.")
        recommended_actions.append("Review the deal and log a current activity.")

    if is_high_priority(request.lead_priority) and is_missing(request.follow_up_due):
        score -= 15
        major_issue_count += 1
        issues.append("High-priority lead has no follow-up due date.")
        recommended_actions.append("Add a follow-up due date for the high-priority lead.")

    if proposal_review_incomplete(request):
        score -= 18
        major_issue_count += 1
        issues.append("Proposal is pending while human review is incomplete.")
        recommended_actions.append("Complete proposal review before customer-facing use.")

    if request.days_in_stage > VERY_LONG_STAGE_DAYS:
        score -= 15
        major_issue_count += 1
        issues.append("Deal has been in stage too long.")
        recommended_actions.append("Review stage fit and confirm whether the deal should advance.")
    elif request.days_in_stage > LONG_STAGE_DAYS:
        score -= 10
        issues.append("Deal is approaching a stale stage threshold.")
        recommended_actions.append("Confirm whether the current deal stage is still accurate.")

    if missing_fields:
        penalty = min(20, 5 * len(missing_fields))
        score -= penalty
        issues.append("Required CRM fields are missing.")
        recommended_actions.append("Fill required CRM fields before relying on automation.")

    open_risks = clean_list(request.open_risks)
    if open_risks:
        score -= min(15, 5 * len(open_risks))
        issues.append("Open deal risks need review.")
        recommended_actions.append("Review open risks and decide the next rep action.")

    hygiene_score = max(0, min(100, score))
    risk_level = classify_risk_level(hygiene_score, major_issue_count)
    human_review_required = (
        risk_level in {"high", "critical"}
        or proposal_review_incomplete(request)
        or is_missing(request.owner)
    )
    confidence = determine_confidence(request, missing_fields)

    return CRMHygieneResponse(
        record_id=request.record_id,
        hygiene_score=hygiene_score,
        risk_level=risk_level,
        issues=issues,
        missing_fields=missing_fields,
        stale_activity=stale_activity,
        recommended_actions=dedupe(recommended_actions),
        human_review_required=human_review_required,
        next_action=determine_next_action(risk_level, issues),
        confidence=confidence,
        reasoning=build_reasoning(hygiene_score, risk_level, issues),
    )


def detect_missing_fields(request: CRMHygieneRequest) -> list[str]:
    missing = [
        field_name
        for field_name, value in request.crm_fields.items()
        if is_missing(value)
    ]
    return sorted(missing)


def is_stale_activity(last_activity_date: str | None) -> bool:
    if is_missing(last_activity_date):
        return False
    try:
        activity_date = date.fromisoformat(str(last_activity_date)[:10])
    except ValueError:
        return True
    return (REFERENCE_DATE - activity_date).days > STALE_ACTIVITY_DAYS


def proposal_review_incomplete(request: CRMHygieneRequest) -> bool:
    return normalize(request.proposal_status) == "pending" and normalize(
        request.human_review_status
    ) not in {"complete", "approved"}


def classify_risk_level(hygiene_score: int, major_issue_count: int) -> str:
    if hygiene_score <= 35 or major_issue_count >= 4:
        return "critical"
    if hygiene_score <= 60 or major_issue_count >= 2:
        return "high"
    if hygiene_score <= 85:
        return "medium"
    return "low"


def determine_confidence(request: CRMHygieneRequest, missing_fields: list[str]) -> str:
    if is_missing(request.last_activity_date):
        return "medium"
    if len(missing_fields) >= 4:
        return "medium"
    return "high"


def determine_next_action(risk_level: str, issues: list[str]) -> str:
    if risk_level == "critical":
        return "RevOps or a sales manager should review this deal before the next customer action."
    if risk_level == "high":
        return "Sales owner should resolve the flagged issues before progressing the deal."
    if issues:
        return "Sales owner should clean up the flagged CRM fields."
    return "No immediate action needed beyond normal deal management."


def build_reasoning(hygiene_score: int, risk_level: str, issues: list[str]) -> str:
    if not issues:
        return f"Risk is {risk_level} because the record is complete and hygiene score is {hygiene_score}."
    return (
        f"Risk is {risk_level} because hygiene score is {hygiene_score} "
        f"and the record has {len(issues)} issue(s)."
    )


def is_high_priority(value: str) -> bool:
    return normalize(value) in {"critical", "high"}


def is_missing(value: object) -> bool:
    return normalize(value) in MISSING_VALUES


def normalize(value: object) -> str:
    return str(value or "").strip().lower()


def clean_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


def dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
