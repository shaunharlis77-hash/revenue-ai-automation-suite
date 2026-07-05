"""Deterministic Workflow 3: Follow-Up Drafting.

This workflow prepares customer-facing follow-up drafts for human review. It
does not send messages, call external services, or make promises on behalf of
the sales team.
"""

from app.models.follow_up import FollowUpDraftRequest, FollowUpDraftResponse
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
    log_step_started,
    log_step_success,
)
from app.services.workflow_audit import (
    audit_completed,
    audit_started,
    audit_workflow_failure,
    record_follow_up_audit,
)


WORKFLOW_NAME = "follow_up_drafting"
RISK_KEYWORDS = ("pricing", "security", "legal", "implementation", "adoption")


def draft_follow_up(request: FollowUpDraftRequest) -> FollowUpDraftResponse:
    workflow_run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name=WORKFLOW_NAME,
            input_reference=request.follow_up_id,
        )
    )
    failed_step = "workflow_started"
    log_step_started(
        workflow_run.workflow_run_id,
        WORKFLOW_NAME,
        "workflow_started",
        1,
        "follow_up",
        request.follow_up_id,
    )

    try:
        audit_started(workflow_run, "follow_up", request.follow_up_id)
        failed_step = "input_validated"
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "input_validated",
            2,
            "follow_up",
            request.follow_up_id,
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "follow_up_context_loaded",
            3,
            "follow_up",
            request.follow_up_id,
            {"company": request.company, "meeting_id": request.meeting_id},
        )
        failed_step = "follow_up_draft_created"
        result = _draft_follow_up(request)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "follow_up_draft_created",
            4,
            "follow_up",
            request.follow_up_id,
            {"confidence": result.confidence},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "guardrails_applied",
            5,
            "follow_up",
            request.follow_up_id,
            {"review_required": result.review_required, "review_reasons": result.review_reasons},
        )
        failed_step = "review_item_created"
        record_follow_up_audit(workflow_run, request, result)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "review_item_created",
            6,
            "follow_up",
            request.follow_up_id,
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "audit_events_written",
            7,
            "follow_up",
            request.follow_up_id,
        )
        mark_workflow_success(
            workflow_run.workflow_run_id,
            WorkflowRunSuccessRequest(
                output_summary=(
                    f"Follow-up draft prepared for {request.company} "
                    f"with {result.confidence} confidence."
                ),
                human_review_required=result.review_required,
                next_action=result.next_action,
            ),
        )
        audit_completed(
            workflow_run,
            "follow_up",
            request.follow_up_id,
            result.follow_up_id,
            result.review_required,
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "workflow_completed",
            8,
            "follow_up",
            request.follow_up_id,
        )
        return result
    except Exception as error:
        log_step_failure(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            failed_step,
            error,
            entity_type="follow_up",
            entity_id=request.follow_up_id,
            failure_reason=str(error),
            retryable=failed_step in {"review_item_created", "audit_events_written"},
            recommended_fix="Check follow-up input context and the review/audit persistence path.",
        )
        mark_workflow_failure(
            workflow_run.workflow_run_id,
            WorkflowRunFailureRequest(
                failure_step=failed_step,
                failure_reason=str(error),
                input_reference=request.follow_up_id,
            ),
        )
        try:
            audit_workflow_failure(
                workflow_run,
                "follow_up",
                request.follow_up_id,
                failed_step,
                str(error),
            )
        except Exception as audit_error:
            log_step_failure(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "audit_events_written",
                audit_error,
                entity_type="follow_up",
                entity_id=request.follow_up_id,
                failure_reason="Audit write failed while recording workflow failure.",
                retryable=True,
                recommended_fix="Check audit event persistence after the follow-up drafting failure.",
                metadata_json={"original_failure_step": failed_step},
            )
        raise


def _draft_follow_up(request: FollowUpDraftRequest) -> FollowUpDraftResponse:
    next_steps = clean_list(request.next_steps)
    pain_points = clean_list(request.pain_points)
    objections = clean_list(request.objections)
    buying_signals = clean_list(request.buying_signals)
    risk_terms = detect_risk_terms(objections)
    missing_next_steps = has_missing_next_steps(next_steps)

    confidence = determine_confidence(missing_next_steps, risk_terms)
    review_reasons = build_review_reasons(missing_next_steps, risk_terms)
    risk_notes = build_risk_notes(risk_terms, missing_next_steps)
    recommended_send_timing = determine_send_timing(
        request.follow_up_due, missing_next_steps
    )
    next_action = determine_next_action(missing_next_steps, risk_terms)

    return FollowUpDraftResponse(
        follow_up_id=request.follow_up_id,
        draft_subject=build_subject(request),
        draft_body=build_body(
            request=request,
            pain_points=pain_points,
            objections=objections,
            buying_signals=buying_signals,
            next_steps=next_steps,
            missing_next_steps=missing_next_steps,
        ),
        message_channel=request.message_channel,
        tone=request.tone,
        source_context_summary=build_source_context_summary(
            request=request,
            pain_points=pain_points,
            objections=objections,
            buying_signals=buying_signals,
        ),
        review_required=True,
        review_reasons=review_reasons,
        risk_notes=risk_notes,
        recommended_send_timing=recommended_send_timing,
        next_action=next_action,
        confidence=confidence,
        reasoning=build_reasoning(confidence, missing_next_steps, risk_terms),
    )


def clean_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


def normalize(value: str) -> str:
    return value.strip().lower()


def has_missing_next_steps(next_steps: list[str]) -> bool:
    if not next_steps:
        return True
    return all(
        normalize(step) in {"confirm next step", "not_set", "unknown", "none"}
        for step in next_steps
    )


def detect_risk_terms(objections: list[str]) -> list[str]:
    detected: list[str] = []
    combined = " ".join(objections).lower()
    for keyword in RISK_KEYWORDS:
        if keyword in combined:
            detected.append(keyword)
    return detected


def determine_confidence(missing_next_steps: bool, risk_terms: list[str]) -> str:
    if missing_next_steps:
        return "low"
    if risk_terms:
        return "medium"
    return "high"


def build_review_reasons(missing_next_steps: bool, risk_terms: list[str]) -> list[str]:
    reasons = ["Customer-facing draft requires sales rep review."]
    if missing_next_steps:
        reasons.append("Next step is missing or unclear.")
    for risk in risk_terms:
        reasons.append(f"{risk.title()} risk needs review.")
    return reasons


def build_risk_notes(risk_terms: list[str], missing_next_steps: bool) -> list[str]:
    notes: list[str] = []
    if missing_next_steps:
        notes.append("Ask the rep to confirm the next step before sending.")
    for risk in risk_terms:
        notes.append(f"Do not make {risk} promises in the follow-up.")
    return notes or ["No special risk language detected, but rep review is still required."]


def determine_send_timing(follow_up_due: str, missing_next_steps: bool) -> str:
    if missing_next_steps:
        return "after_next_step_confirmed"
    due = normalize(follow_up_due)
    if due in {"today", "tomorrow", "next_week"}:
        return due
    if due == "thursday":
        return "Thursday"
    return "after_rep_review"


def determine_next_action(missing_next_steps: bool, risk_terms: list[str]) -> str:
    if missing_next_steps:
        return "Rep should confirm the next step, then review the draft before sending."
    if risk_terms:
        return "Rep should review risk-sensitive wording before sending."
    return "Rep should review and approve the draft before sending."


def build_subject(request: FollowUpDraftRequest) -> str:
    return f"Follow-up from {request.rep_name}"


def build_body(
    request: FollowUpDraftRequest,
    pain_points: list[str],
    objections: list[str],
    buying_signals: list[str],
    next_steps: list[str],
    missing_next_steps: bool,
) -> str:
    greeting = f"Hi {request.contact_name},"
    thanks = f"Thanks for the conversation about {request.company}."
    context_parts: list[str] = []

    if pain_points:
        context_parts.append(f"We discussed {format_items(pain_points)}.")
    if buying_signals:
        context_parts.append(f"I also noted {format_items(buying_signals)}.")
    if objections:
        context_parts.append(
            f"I understand the team is still considering {format_items(objections)}."
        )

    if missing_next_steps:
        next_step_text = (
            "Before I send anything more detailed, could you confirm the best next "
            "step and who should be included?"
        )
    else:
        next_step_text = f"Next, I will follow up on {format_items(next_steps)}."

    close = f"Best,\n{request.rep_name}"
    return "\n\n".join([greeting, thanks, *context_parts, next_step_text, close])


def format_items(items: list[str]) -> str:
    if not items:
        return "the next steps"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def build_source_context_summary(
    request: FollowUpDraftRequest,
    pain_points: list[str],
    objections: list[str],
    buying_signals: list[str],
) -> str:
    parts = [
        f"Lead priority is {request.lead_priority}.",
        f"Deal stage recommendation is {request.deal_stage_recommendation}.",
    ]
    if pain_points:
        parts.append(f"Pain points: {format_items(pain_points)}.")
    if objections:
        parts.append(f"Objections: {format_items(objections)}.")
    if buying_signals:
        parts.append(f"Buying signals: {format_items(buying_signals)}.")
    return " ".join(parts)


def build_reasoning(
    confidence: str, missing_next_steps: bool, risk_terms: list[str]
) -> str:
    if missing_next_steps:
        return "Draft has low confidence because the next step is missing or unclear."
    if risk_terms:
        return (
            "Draft has medium confidence because risk-sensitive topics need review: "
            f"{format_items(risk_terms)}."
        )
    return "Draft has high confidence because the context and next steps are clear."
