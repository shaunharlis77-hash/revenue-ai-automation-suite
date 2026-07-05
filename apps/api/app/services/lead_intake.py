from uuid import uuid4

from app.models.audit import AuditEventCreate
from app.models.lead_intake import (
    LeadEnrichmentResult,
    LeadIntakeRequest,
    LeadIntakeResponse,
)
from app.models.lead_scoring import LeadScoringRequest, LeadScoringResponse
from app.models.review_queue import ReviewItemCreate
from app.models.workflow_logs import (
    WorkflowRunFailureRequest,
    WorkflowRunStartRequest,
    WorkflowRunSuccessRequest,
)
from app.services.audit_trail import create_audit_event
from app.services.crm_adapter_factory import get_crm_adapter
from app.services.lead_enrichment import enrich_lead
from app.services.lead_scoring import _score_lead
from app.services.review_queue import create_review_item
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


WORKFLOW_NAME = "lead_intake_enrichment"
DEMO_METADATA_KEY = "lead_intake"


def intake_lead(request: LeadIntakeRequest) -> LeadIntakeResponse:
    lead_id = f"lead_{uuid4()}"
    entity_id = lead_id
    contact_name = full_name(request)
    workflow_run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name=WORKFLOW_NAME,
            input_reference=request.email,
        )
    )
    failed_step = "workflow_started"
    log_step_started(
        workflow_run.workflow_run_id,
        WORKFLOW_NAME,
        "workflow_started",
        1,
        "lead",
        entity_id,
    )

    try:
        write_audit_event(
            workflow_run.workflow_run_id,
            "workflow_started",
            entity_id,
            request.email,
            metadata={"company": request.company},
        )
        failed_step = "input_validated"
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "input_validated",
            2,
            "lead",
            entity_id,
        )

        failed_step = "lead_received"
        write_audit_event(
            workflow_run.workflow_run_id,
            "lead_received",
            entity_id,
            request.email,
            metadata={"source": request.source},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "lead_received",
            3,
            "lead",
            entity_id,
            {"source": request.source},
        )

        failed_step = "lead_enriched"
        enrichment = enrich_lead(request)
        write_audit_event(
            workflow_run.workflow_run_id,
            "lead_enriched",
            entity_id,
            request.email,
            metadata={
                "persona": enrichment.persona,
                "confidence": enrichment.enrichment_confidence,
                "risk_flags": enrichment.enrichment_risk_flags,
            },
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "lead_enriched",
            4,
            "lead",
            entity_id,
            {
                "persona": enrichment.persona,
                "enrichment_confidence": enrichment.enrichment_confidence,
                "risk_flags": enrichment.enrichment_risk_flags,
            },
        )

        failed_step = "lead_scored"
        scoring_request = build_scoring_request(lead_id, request)
        score = _score_lead(scoring_request)
        write_audit_event(
            workflow_run.workflow_run_id,
            "lead_scored",
            entity_id,
            lead_id,
            human_review_required=score.human_review_required,
            metadata={"lead_score": score.lead_score, "priority": score.priority},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "lead_scored",
            5,
            "lead",
            entity_id,
            {"lead_score": score.lead_score, "priority": score.priority},
        )

        failed_step = "route_recommended"
        write_audit_event(
            workflow_run.workflow_run_id,
            "route_recommended",
            entity_id,
            lead_id,
            human_review_required=score.human_review_required,
            metadata={"recommended_route": score.recommended_route},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "route_recommended",
            6,
            "lead",
            entity_id,
            {"recommended_route": score.recommended_route},
        )

        failed_step = "crm_update_evaluated"
        decision = evaluate_crm_update(enrichment, score)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "crm_update_evaluated",
            7,
            "lead",
            entity_id,
            {
                "crm_update_status": decision["status"],
                "review_reasons": decision["review_reasons"],
            },
        )

        failed_step = "crm_adapter_write_failed"
        crm_adapter = get_crm_adapter()
        crm_record = crm_adapter.create_or_update_lead_record(
            lead_id=lead_id,
            request=request,
            enrichment=enrichment,
            score=score,
            crm_update_status=decision["status"],
            human_review_required=decision["review_required"],
            risk_flags=decision["risk_flags"],
            workflow_run_id=workflow_run.workflow_run_id,
        )
        crm_step = (
            "crm_update_blocked"
            if decision["status"] == "blocked_pending_review"
            else "crm_update_applied"
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            crm_step,
            8,
            "lead",
            entity_id,
            {"crm_update_status": decision["status"]},
        )

        failed_step = "review_item_created_if_required"
        review_created = False
        if decision["review_required"]:
            create_review_item(
                ReviewItemCreate(
                    workflow_run_id=workflow_run.workflow_run_id,
                    workflow_name=WORKFLOW_NAME,
                    entity_type="lead",
                    entity_id=lead_id,
                    company=request.company,
                    contact_name=contact_name,
                    review_type="lead_routing"
                    if decision["status"] != "blocked_pending_review"
                    else "crm_update",
                    title=f"Review lead intake outcome for {request.company}",
                    priority=score.priority,
                    risk_level=decision["risk_level"],
                    review_reasons=decision["review_reasons"],
                    proposed_action=score.next_best_action,
                    proposed_output=score.recommended_route,
                    metadata_json={
                        DEMO_METADATA_KEY: True,
                        "crm_update_status": decision["status"],
                        "lead_score": score.lead_score,
                    },
                )
            )
            review_created = True
            log_step_success(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "review_item_created_if_required",
                9,
                "lead",
                entity_id,
                {"review_reasons": decision["review_reasons"]},
            )
        else:
            log_step_skipped(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "review_item_created_if_required",
                "No review item required for clean automatic lead intake.",
                9,
                "lead",
                entity_id,
            )

        failed_step = "audit_events_written"
        write_crm_update_audit(
            workflow_run.workflow_run_id,
            entity_id,
            lead_id,
            decision["status"],
            decision["review_required"],
            decision["review_reasons"],
        )
        if decision["review_required"]:
            write_audit_event(
                workflow_run.workflow_run_id,
                "guardrail_triggered",
                entity_id,
                lead_id,
                guardrails=decision["review_reasons"],
                human_review_required=True,
                metadata={"crm_update_status": decision["status"]},
            )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "audit_events_written",
            10,
            "lead",
            entity_id,
        )

        response = LeadIntakeResponse(
            lead_id=lead_id,
            crm_record=crm_record,
            enrichment=enrichment,
            lead_score=score.lead_score,
            priority=score.priority,
            confidence=score.confidence,
            urgency=score.urgency,
            recommended_route=score.recommended_route,
            next_best_action=score.next_best_action,
            crm_update_status=decision["status"],
            review_created=review_created,
            review_reasons=decision["review_reasons"],
            workflow_run_id=workflow_run.workflow_run_id,
            reasoning=build_reasoning(decision["status"], score, enrichment),
        )

        mark_workflow_success(
            workflow_run.workflow_run_id,
            WorkflowRunSuccessRequest(
                output_summary=(
                    f"Lead intake completed with score {score.lead_score}, "
                    f"{score.priority} priority, and CRM update status {decision['status']}."
                ),
                human_review_required=decision["review_required"],
                next_action=score.next_best_action,
            ),
        )
        write_audit_event(
            workflow_run.workflow_run_id,
            "workflow_completed",
            entity_id,
            lead_id,
            human_review_required=decision["review_required"],
            metadata={"crm_record_id": crm_record.crm_record_id},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "workflow_completed",
            11,
            "lead",
            entity_id,
        )
        return response
    except Exception as error:
        retryable_steps = {
            "lead_enriched",
            "crm_update_applied",
            "crm_adapter_write_failed",
            "audit_events_written",
        }
        log_step_failure(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            failed_step,
            error,
            entity_type="lead",
            entity_id=entity_id,
            failure_reason=str(error),
            retryable=failed_step in retryable_steps,
            recommended_fix=recommended_fix_for_step(failed_step),
        )
        mark_workflow_failure(
            workflow_run.workflow_run_id,
            WorkflowRunFailureRequest(
                failure_step=failed_step,
                failure_reason=str(error),
                input_reference=request.email,
                human_review_required=True,
                next_action="Review the failed lead intake workflow before retrying.",
            ),
        )
        try:
            write_audit_event(
                workflow_run.workflow_run_id,
                "workflow_failed",
                entity_id,
                request.email,
                human_review_required=True,
                metadata={"failure_step": failed_step, "failure_reason": str(error)},
            )
        except Exception as audit_error:
            log_step_failure(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "audit_events_written",
                audit_error,
                entity_type="lead",
                entity_id=entity_id,
                failure_reason="Audit write failed while recording lead intake failure.",
                retryable=True,
                recommended_fix="Check audit event persistence after the lead intake failure.",
                metadata_json={"original_failure_step": failed_step},
            )
        raise


def build_scoring_request(lead_id: str, request: LeadIntakeRequest) -> LeadScoringRequest:
    message_parts = [
        request.message or "",
        request.notes or "",
        " ".join(request.pain_points),
    ]
    return LeadScoringRequest(
        lead_id=lead_id,
        name=full_name(request) or request.email,
        email=request.email,
        company=request.company,
        role=request.job_title or "Unknown",
        company_size=request.company_size or "unknown",
        source="demo_request" if request.requested_demo else request.source,
        message=" ".join(part for part in message_parts if part).strip(),
        timeline=normalize_timeline(request.urgency),
        budget=normalize_budget(request.budget_context),
        current_crm=request.crm_system or "unknown",
    )


def evaluate_crm_update(
    enrichment: LeadEnrichmentResult, score: LeadScoringResponse
) -> dict:
    risk_flags = list(enrichment.enrichment_risk_flags)
    review_reasons: list[str] = []

    high_priority = score.priority in {"critical", "high"}
    blocking_reasons: list[str] = []
    visibility_reasons: list[str] = []

    if high_priority:
        visibility_reasons.append("High-priority lead routed automatically with review visibility.")
    if enrichment.enrichment_confidence == "low":
        blocking_reasons.append("Enrichment confidence is low.")
    if score.confidence == "low":
        blocking_reasons.append("Lead score confidence is low.")
    if score.priority == "disqualify":
        blocking_reasons.append("Lead may be test, spam-like, or disqualified.")
    if "suspicious_or_test_submission" in risk_flags:
        blocking_reasons.append("Suspicious or test-like lead signals detected.")
    if not score.recommended_route or score.recommended_route == "Human review queue for qualification":
        blocking_reasons.append("Routing is ambiguous or requires qualification review.")

    if blocking_reasons:
        status = "blocked_pending_review"
        risk_level = "high"
        review_reasons = blocking_reasons
    elif high_priority:
        status = "applied_with_review_visibility"
        risk_level = "medium"
        review_reasons = visibility_reasons
    else:
        status = "applied"
        risk_level = "low"

    return {
        "status": status,
        "review_required": status != "applied",
        "review_reasons": review_reasons,
        "risk_flags": risk_flags,
        "risk_level": risk_level,
    }


def write_crm_update_audit(
    workflow_run_id: str,
    entity_id: str,
    output_reference: str,
    crm_update_status: str,
    human_review_required: bool,
    guardrails: list[str],
) -> None:
    event_type = {
        "applied": "crm_update_applied",
        "applied_with_review_visibility": "crm_update_applied_with_review_visibility",
        "blocked_pending_review": "crm_update_blocked",
    }[crm_update_status]
    write_audit_event(
        workflow_run_id,
        event_type,
        entity_id,
        output_reference,
        guardrails=guardrails if crm_update_status == "blocked_pending_review" else [],
        human_review_required=human_review_required,
        metadata={"crm_update_status": crm_update_status},
    )


def write_audit_event(
    workflow_run_id: str,
    event_type: str,
    entity_id: str,
    output_reference: str | None = None,
    guardrails: list[str] | None = None,
    human_review_required: bool = False,
    metadata: dict | None = None,
) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=workflow_run_id,
            workflow_name=WORKFLOW_NAME,
            entity_type="lead",
            entity_id=entity_id,
            event_type=event_type,
            event_source="lead_intake",
            actor="system",
            output_reference=output_reference,
            guardrails_triggered=guardrails or [],
            human_review_required=human_review_required,
            metadata_json=metadata or {},
        )
    )


def full_name(request: LeadIntakeRequest) -> str:
    return " ".join(
        part.strip()
        for part in [request.first_name or "", request.last_name or ""]
        if part and part.strip()
    )


def normalize_timeline(value: str | None) -> str:
    urgency = str(value or "").strip().lower()
    if urgency in {"urgent", "critical", "immediate"}:
        return "urgent"
    if urgency in {"this_week", "this week", "week"}:
        return "this_week"
    if urgency in {"30_days", "30 days", "month", "this_month"}:
        return "30_days"
    if urgency in {"none", "not urgent"}:
        return "none"
    return "unknown"


def normalize_budget(value: str | None) -> str:
    budget = str(value or "").strip().lower()
    if "approved" in budget:
        return "approved"
    if "planned" in budget:
        return "planned"
    if "limited" in budget or "tight" in budget:
        return "limited"
    if budget in {"none", "no budget"}:
        return "none"
    return "unknown"


def build_reasoning(
    crm_update_status: str,
    score: LeadScoringResponse,
    enrichment: LeadEnrichmentResult,
) -> str:
    return (
        f"Lead intake used deterministic enrichment with {enrichment.enrichment_confidence} "
        f"confidence and scoring priority {score.priority}. CRM update status is "
        f"{crm_update_status}."
    )


def recommended_fix_for_step(step_name: str) -> str:
    fixes = {
        "lead_enriched": "Check enrichment input fields and deterministic enrichment rules.",
        "crm_update_applied": "Check the internal CRM lead record persistence path.",
        "crm_adapter_write_failed": "Check the mock CRM adapter persistence path and retry lead intake.",
        "audit_events_written": "Check audit event persistence for lead intake.",
    }
    return fixes.get(step_name, "Check lead intake input, persistence, and workflow logs.")
