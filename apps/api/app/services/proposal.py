"""Deterministic Workflow 4: Proposal / Package Outline Drafting.

This service creates an internal outline for sales review. It does not create a
final customer-ready proposal, send messages, or make pricing, legal, security,
or implementation commitments.
"""

from app.models.proposal import ProposalDraftRequest, ProposalDraftResponse
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
    record_proposal_audit,
)


WORKFLOW_NAME = "proposal_outline_drafting"
RISK_KEYWORDS = ("pricing", "security", "legal", "implementation", "adoption", "budget")
MISSING_VALUES = {"", "unknown", "none", "not_set", "n/a", "na", "unclear"}


def draft_proposal(request: ProposalDraftRequest) -> ProposalDraftResponse:
    workflow_run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name=WORKFLOW_NAME,
            input_reference=request.proposal_id,
        )
    )
    failed_step = "workflow_started"
    log_step_started(
        workflow_run.workflow_run_id,
        WORKFLOW_NAME,
        "workflow_started",
        1,
        "proposal",
        request.proposal_id,
    )

    try:
        audit_started(workflow_run, "proposal", request.proposal_id)
        failed_step = "input_validated"
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "input_validated",
            2,
            "proposal",
            request.proposal_id,
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "proposal_context_loaded",
            3,
            "proposal",
            request.proposal_id,
            {"company": request.company, "meeting_id": request.meeting_id},
        )
        failed_step = "proposal_outline_created"
        result = _draft_proposal(request)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "proposal_outline_created",
            4,
            "proposal",
            request.proposal_id,
            {"confidence": result.confidence},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "risk_notes_created",
            5,
            "proposal",
            request.proposal_id,
            {"risk_notes": result.risk_notes},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "guardrails_applied",
            6,
            "proposal",
            request.proposal_id,
            {"review_reasons": result.review_reasons},
        )
        failed_step = "review_item_created"
        record_proposal_audit(workflow_run, request, result)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "review_item_created",
            7,
            "proposal",
            request.proposal_id,
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "audit_events_written",
            8,
            "proposal",
            request.proposal_id,
        )
        mark_workflow_success(
            workflow_run.workflow_run_id,
            WorkflowRunSuccessRequest(
                output_summary=(
                    f"Proposal outline prepared for {request.company} "
                    f"with {result.confidence} confidence."
                ),
                human_review_required=result.human_review_required,
                next_action=result.next_action,
            ),
        )
        audit_completed(
            workflow_run,
            "proposal",
            request.proposal_id,
            result.proposal_id,
            result.human_review_required,
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "workflow_completed",
            9,
            "proposal",
            request.proposal_id,
        )
        return result
    except Exception as error:
        log_step_failure(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            failed_step,
            error,
            entity_type="proposal",
            entity_id=request.proposal_id,
            failure_reason=str(error),
            retryable=failed_step in {"review_item_created", "audit_events_written"},
            recommended_fix="Check proposal input context and the review/audit persistence path.",
        )
        mark_workflow_failure(
            workflow_run.workflow_run_id,
            WorkflowRunFailureRequest(
                failure_step=failed_step,
                failure_reason=str(error),
                input_reference=request.proposal_id,
            ),
        )
        try:
            audit_workflow_failure(
                workflow_run,
                "proposal",
                request.proposal_id,
                failed_step,
                str(error),
            )
        except Exception as audit_error:
            log_step_failure(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "audit_events_written",
                audit_error,
                entity_type="proposal",
                entity_id=request.proposal_id,
                failure_reason="Audit write failed while recording workflow failure.",
                retryable=True,
                recommended_fix="Check audit event persistence after the proposal drafting failure.",
                metadata_json={"original_failure_step": failed_step},
            )
        raise


def _draft_proposal(request: ProposalDraftRequest) -> ProposalDraftResponse:
    pain_points = clean_list(request.pain_points)
    objections = clean_list(request.objections)
    buying_signals = clean_list(request.buying_signals)
    next_steps = clean_list(request.next_steps)
    risk_areas = clean_list(request.risk_areas)

    risk_terms = detect_risk_terms(objections, risk_areas)
    budget_missing = is_missing(request.budget_context)
    timeline_risk = classify_timeline_risk(request.implementation_timeline)
    missing_context = not pain_points or not next_steps

    confidence = determine_confidence(
        budget_missing=budget_missing,
        timeline_risk=timeline_risk,
        missing_context=missing_context,
        risk_terms=risk_terms,
    )
    review_reasons = build_review_reasons(
        budget_missing=budget_missing,
        timeline_risk=timeline_risk,
        missing_context=missing_context,
        risk_terms=risk_terms,
    )
    risk_notes = build_risk_notes(
        budget_missing=budget_missing,
        timeline_risk=timeline_risk,
        missing_context=missing_context,
        risk_terms=risk_terms,
    )

    return ProposalDraftResponse(
        proposal_id=request.proposal_id,
        proposal_title=f"{request.company} {request.requested_package_type} Outline",
        executive_summary=build_executive_summary(request, buying_signals),
        problem_statement=build_problem_statement(pain_points),
        recommended_package=build_recommended_package(request),
        scope_items=build_scope_items(pain_points, next_steps),
        implementation_considerations=build_implementation_considerations(
            request, timeline_risk
        ),
        assumptions=build_assumptions(request, buying_signals),
        exclusions=build_exclusions(),
        risk_notes=risk_notes,
        review_reasons=review_reasons,
        confidence=confidence,
        human_review_required=True,
        next_action=determine_next_action(confidence, risk_terms, missing_context),
        reasoning=build_reasoning(confidence, budget_missing, timeline_risk, missing_context),
    )


def clean_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


def normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def is_missing(value: str | None) -> bool:
    return normalize(value) in MISSING_VALUES


def detect_risk_terms(objections: list[str], risk_areas: list[str]) -> list[str]:
    combined = " ".join([*objections, *risk_areas]).lower()
    detected: list[str] = []
    for keyword in RISK_KEYWORDS:
        if keyword in combined:
            detected.append(keyword)
    return detected


def classify_timeline_risk(implementation_timeline: str) -> str | None:
    timeline = normalize(implementation_timeline)
    if timeline in MISSING_VALUES:
        return "unclear"
    if any(term in timeline for term in ("urgent", "this_week", "this week", "before monday")):
        return "urgent"
    return None


def determine_confidence(
    budget_missing: bool,
    timeline_risk: str | None,
    missing_context: bool,
    risk_terms: list[str],
) -> str:
    if missing_context and (budget_missing or timeline_risk):
        return "low"
    if budget_missing or timeline_risk or missing_context or risk_terms:
        return "medium"
    return "high"


def build_review_reasons(
    budget_missing: bool,
    timeline_risk: str | None,
    missing_context: bool,
    risk_terms: list[str],
) -> list[str]:
    reasons = ["Internal proposal outline requires sales rep review."]
    if budget_missing:
        reasons.append("Budget context is missing or unclear.")
    if timeline_risk == "urgent":
        reasons.append("Implementation timeline is urgent.")
    if timeline_risk == "unclear":
        reasons.append("Implementation timeline is missing or unclear.")
    if missing_context:
        reasons.append("Pain points or next steps are missing.")
    for risk in risk_terms:
        reasons.append(f"{risk.title()} concern needs review.")
    return dedupe(reasons)


def build_risk_notes(
    budget_missing: bool,
    timeline_risk: str | None,
    missing_context: bool,
    risk_terms: list[str],
) -> list[str]:
    notes: list[str] = []
    if budget_missing:
        notes.append("Confirm budget context before discussing package fit.")
    if timeline_risk == "urgent":
        notes.append("Validate implementation timing before sharing any timeline externally.")
    if timeline_risk == "unclear":
        notes.append("Confirm implementation timeline before scope is reviewed.")
    if missing_context:
        notes.append("Confirm pain points and next steps before using this outline.")
    for risk in risk_terms:
        notes.append(f"Review {risk} language before this becomes customer-facing.")
    return dedupe(notes) or ["No special risk areas detected, but review is still required."]


def build_executive_summary(
    request: ProposalDraftRequest, buying_signals: list[str]
) -> str:
    signal_text = (
        f" Buying signals include {format_items(buying_signals)}."
        if buying_signals
        else ""
    )
    return (
        f"This internal outline frames a {request.requested_package_type} package "
        f"for {request.company} based on current discovery context.{signal_text}"
    )


def build_problem_statement(pain_points: list[str]) -> str:
    if not pain_points:
        return "The core business problem needs more discovery before scope is finalized."
    return f"The current problems are {format_items(pain_points)}."


def build_recommended_package(request: ProposalDraftRequest) -> str:
    return (
        f"Recommended package: {request.requested_package_type}. This is an internal "
        "outline for review, not a customer-ready pricing document."
    )


def build_scope_items(pain_points: list[str], next_steps: list[str]) -> list[str]:
    items: list[str] = []
    for pain_point in pain_points:
        items.append(f"Address {pain_point}.")
    for next_step in next_steps:
        items.append(f"Prepare for next step: {next_step}.")
    return items or ["Confirm scope after additional discovery."]


def build_implementation_considerations(
    request: ProposalDraftRequest, timeline_risk: str | None
) -> list[str]:
    considerations = [
        f"Current CRM context: {request.current_crm}.",
        f"Implementation timeline context: {request.implementation_timeline}.",
    ]
    if timeline_risk:
        considerations.append("Timeline should be validated before sharing externally.")
    return considerations


def build_assumptions(
    request: ProposalDraftRequest, buying_signals: list[str]
) -> list[str]:
    assumptions = [
        "Sales rep will review and approve the outline before customer use.",
        f"Budget context provided: {request.budget_context}.",
    ]
    if buying_signals:
        assumptions.append(f"Buying signals considered: {format_items(buying_signals)}.")
    return assumptions


def build_exclusions() -> list[str]:
    return [
        "No pricing is included.",
        "No legal, security, compliance, or implementation commitments are included.",
        "This outline is not customer-ready until reviewed and approved.",
    ]


def determine_next_action(
    confidence: str, risk_terms: list[str], missing_context: bool
) -> str:
    if confidence == "low":
        return "Rep should confirm missing budget, timeline, pain points, and next steps before using the outline."
    if risk_terms or missing_context:
        return "Rep should review risk notes and adjust the outline before customer use."
    return "Rep should review and approve the internal outline before customer use."


def build_reasoning(
    confidence: str,
    budget_missing: bool,
    timeline_risk: str | None,
    missing_context: bool,
) -> str:
    reasons: list[str] = []
    if budget_missing:
        reasons.append("budget context is missing or unclear")
    if timeline_risk:
        reasons.append(f"implementation timeline is {timeline_risk}")
    if missing_context:
        reasons.append("pain points or next steps need more detail")
    if reasons:
        return f"Confidence is {confidence} because {format_items(reasons)}."
    return "Confidence is high because the outline has clear pain, budget, timeline, and next-step context."


def format_items(items: list[str]) -> str:
    if not items:
        return "the available context"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
