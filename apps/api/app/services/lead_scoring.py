"""First version of lead scoring for Workflow 1.

The service uses deterministic rules only so the logic stays easy to test and
explain before any LLM or CRM integration is added.
"""

from app.models.lead_scoring import LeadScoringRequest, LeadScoringResponse, Priority
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
    record_lead_scoring_audit,
)


WORKFLOW_NAME = "lead_scoring_routing"
MISSING_VALUES = {"", "unknown", "none", "n/a", "na"}
SPAM_SIGNALS = ("test", "student", "school assignment", "please ignore")


def normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def is_missing(value: str | None) -> bool:
    return normalize(value) in MISSING_VALUES


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = normalize(text)
    return any(keyword in normalized for keyword in keywords)


def score_lead(lead: LeadScoringRequest) -> LeadScoringResponse:
    workflow_run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name=WORKFLOW_NAME,
            input_reference=lead.lead_id or lead.email,
        )
    )
    entity_id = lead.lead_id or lead.email
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
        audit_started(workflow_run, "lead", entity_id)
        failed_step = "input_validated"
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "input_validated",
            2,
            "lead",
            entity_id,
        )
        failed_step = "lead_scored"
        result = _score_lead(lead)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "lead_scored",
            3,
            "lead",
            entity_id,
            {"lead_score": result.lead_score, "priority": result.priority},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "route_recommended",
            4,
            "lead",
            entity_id,
            {"recommended_route": result.recommended_route},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "review_requirement_evaluated",
            5,
            "lead",
            entity_id,
            {"human_review_required": result.human_review_required},
        )
        failed_step = "audit_events_written"
        record_lead_scoring_audit(workflow_run, lead, result)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "audit_events_written",
            6,
            "lead",
            entity_id,
        )
        mark_workflow_success(
            workflow_run.workflow_run_id,
            WorkflowRunSuccessRequest(
                output_summary=(
                    f"Lead scored {result.lead_score} with {result.priority} priority "
                    f"and {result.confidence} confidence."
                ),
                human_review_required=result.human_review_required,
                next_action=result.next_best_action,
            ),
        )
        audit_completed(
            workflow_run,
            "lead",
            entity_id,
            result.lead_id or entity_id,
            result.human_review_required,
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "workflow_completed",
            7,
            "lead",
            entity_id,
        )
        return result
    except Exception as error:
        log_step_failure(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            failed_step,
            error,
            entity_type="lead",
            entity_id=entity_id,
            failure_reason=str(error),
            retryable=failed_step == "audit_events_written",
            recommended_fix="Check the lead input and the audit/review persistence path.",
        )
        mark_workflow_failure(
            workflow_run.workflow_run_id,
            WorkflowRunFailureRequest(
                failure_step=failed_step,
                failure_reason=str(error),
                input_reference=lead.lead_id or lead.email,
            ),
        )
        try:
            audit_workflow_failure(
                workflow_run,
                "lead",
                lead.lead_id or lead.email,
                failed_step,
                str(error),
            )
        except Exception as audit_error:
            log_step_failure(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "audit_events_written",
                audit_error,
                entity_type="lead",
                entity_id=entity_id,
                failure_reason="Audit write failed while recording workflow failure.",
                retryable=True,
                recommended_fix="Check audit event persistence after the lead scoring failure.",
                metadata_json={"original_failure_step": failed_step},
            )
        raise


def _score_lead(lead: LeadScoringRequest) -> LeadScoringResponse:
    if is_test_or_spam(lead):
        return LeadScoringResponse(
            lead_id=lead.lead_id,
            lead_score=5,
            priority="disqualify",
            persona="Student or test submission",
            pain_points=["None"],
            urgency="none",
            recommended_route="Do not route to sales",
            next_best_action="Mark as test or spam-like lead after review.",
            confidence="high",
            human_review_required=True,
            reasoning="The submission contains test, student, school assignment, or please-ignore signals.",
        )

    score = 12
    reasons: list[str] = []

    score += source_points(lead.source, reasons)
    score += timeline_points(lead.timeline, reasons)
    score += budget_points(lead.budget, reasons)
    score += role_points(lead.role, reasons)
    score += company_size_points(lead.company_size, reasons)
    score += crm_points(lead.current_crm, reasons)
    score += message_points(lead.message, reasons)

    missing_count = count_missing_fields(lead)
    if missing_count:
        reasons.append(f"{missing_count} important field(s) are missing or unknown")

    urgency = classify_urgency(lead.timeline, lead.message)
    lead_score = cap_score(score, urgency)
    confidence = classify_confidence(lead, lead_score, missing_count)
    priority = classify_priority(lead_score, urgency)
    persona = classify_persona(lead.role)
    pain_points = detect_pain_points(lead.message)
    human_review_required = needs_human_review(lead, priority, confidence, missing_count)

    return LeadScoringResponse(
        lead_id=lead.lead_id,
        lead_score=lead_score,
        priority=priority,
        persona=persona,
        pain_points=pain_points,
        urgency=urgency,
        recommended_route=recommended_route(priority, persona, confidence),
        next_best_action=next_best_action(priority, confidence, urgency),
        confidence=confidence,
        human_review_required=human_review_required,
        reasoning=build_reasoning(reasons, priority, confidence),
    )


def is_test_or_spam(lead: LeadScoringRequest) -> bool:
    combined = " ".join(
        [
            lead.name,
            lead.email,
            lead.company,
            lead.role,
            lead.source,
            lead.message,
        ]
    )
    return contains_any(combined, SPAM_SIGNALS)


def source_points(source: str, reasons: list[str]) -> int:
    values = {
        "demo_request": (22, "high-intent demo request"),
        "implementation_request": (25, "implementation request"),
        "pricing_page": (15, "pricing page interest"),
        "partner_referral": (18, "partner referral"),
        "webinar": (8, "webinar engagement"),
        "content_download": (8, "content download"),
        "contact_form": (2, "general contact form"),
    }
    points, reason = values.get(normalize(source), (0, "unrecognized lead source"))
    reasons.append(reason)
    return points


def timeline_points(timeline: str, reasons: list[str]) -> int:
    values = {
        "urgent": (22, "urgent timeline"),
        "this_week": (14, "this-week timeline"),
        "30_days": (12, "30-day timeline"),
        "60_days": (8, "60-day timeline"),
        "90_days": (4, "90-day timeline"),
        "unknown": (-4, "unknown timeline"),
        "none": (-10, "no timeline"),
    }
    points, reason = values.get(normalize(timeline), (0, "timeline not scored"))
    reasons.append(reason)
    return points


def budget_points(budget: str, reasons: list[str]) -> int:
    values = {
        "approved": (14, "approved budget"),
        "planned": (10, "planned budget"),
        "limited": (2, "limited budget"),
        "low": (-2, "low budget"),
        "unknown": (-4, "unknown budget"),
        "none": (-10, "no budget"),
    }
    points, reason = values.get(normalize(budget), (0, "budget not scored"))
    reasons.append(reason)
    return points


def role_points(role: str, reasons: list[str]) -> int:
    role_value = normalize(role)
    if "head of revenue operations" in role_value:
        reasons.append("senior revenue operations role")
        return 14
    if "revenue operations manager" in role_value:
        reasons.append("revenue operations manager role")
        return 13
    if "vp of sales" in role_value:
        reasons.append("sales leadership role")
        return 12
    if "director of commercial operations" in role_value:
        reasons.append("commercial operations leadership role")
        return 13
    if "founder" in role_value:
        reasons.append("founder role")
        return 7
    if "marketing lead" in role_value:
        reasons.append("marketing operator role")
        return 4
    reasons.append("role has limited buying signal")
    return 0


def company_size_points(company_size: str, reasons: list[str]) -> int:
    size = normalize(company_size)
    if size == "5000+":
        reasons.append("enterprise company size")
        return 14
    if size == "501-1000":
        reasons.append("large mid-market company size")
        return 12
    if size == "201-500":
        reasons.append("strong mid-market company size")
        return 8
    if size == "51-200":
        reasons.append("mid-market company size")
        return 8
    if size == "11-50":
        reasons.append("small company size")
        return 4
    if size == "1-10":
        reasons.append("very small company size")
        return -2
    reasons.append("unknown company size")
    return -4


def crm_points(current_crm: str, reasons: list[str]) -> int:
    crm = normalize(current_crm)
    if crm in {"hubspot", "salesforce"}:
        reasons.append(f"clear {current_crm} CRM context")
        return 6
    if crm == "pipedrive":
        reasons.append("clear Pipedrive CRM context")
        return 6
    if crm == "none":
        reasons.append("no CRM context")
        return -3
    reasons.append("CRM context not recognized")
    return 0


def message_points(message: str, reasons: list[str]) -> int:
    keyword_groups = [
        (("routing", "route", "handoff", "lead sorting"), 6, "routing or handoff pain"),
        (("lead scoring", "qualifying inbound", "bad fit leads"), 6, "lead qualification pain"),
        (("follow-up", "follow up"), 5, "follow-up automation pain"),
        (("crm cleanup", "cleaning fields", "crm hygiene"), 5, "CRM cleanup pain"),
        (("inbound volume", "sdr queue", "reps"), 6, "rep workload or inbound volume pain"),
        (("sales admin", "sales ops", "sales operations"), 5, "sales operations pain"),
        (("implementation", "live before monday"), 6, "implementation urgency"),
        (("campaign launch", "campaigns"), 3, "campaign readiness signal"),
        (("automation", "automate"), 6, "automation need"),
        (("budget is tight",), 2, "budget sensitivity"),
    ]
    total = 0
    for keywords, points, reason in keyword_groups:
        if contains_any(message, keywords):
            total += points
            reasons.append(reason)

    if is_vague_message(message):
        total -= 8
        reasons.append("message is vague")

    return min(total, 18)


def is_vague_message(message: str) -> bool:
    msg = normalize(message)
    vague_phrases = ("looking around", "learn more", "what you do")
    return len(msg) < 80 and contains_any(msg, vague_phrases)


def count_missing_fields(lead: LeadScoringRequest) -> int:
    values = [
        lead.company_size,
        lead.timeline,
        lead.budget,
        lead.current_crm,
        lead.message,
    ]
    return sum(1 for value in values if is_missing(value))


def classify_urgency(timeline: str, message: str) -> str:
    timeline_value = normalize(timeline)
    if timeline_value == "urgent":
        return "critical"
    if timeline_value in {"this_week"}:
        return "high"
    if timeline_value in {"30_days", "60_days"}:
        return "medium"
    if timeline_value == "90_days":
        return "low"
    if timeline_value == "none":
        return "none"
    if timeline_value == "unknown" and is_vague_message(message):
        return "low"
    return "unknown"


def cap_score(score: int, urgency: str) -> int:
    bounded_score = max(20, min(100, score))
    if urgency == "critical":
        return min(97, bounded_score)
    return min(94, bounded_score)


def classify_priority(score: int, urgency: str) -> Priority:
    if score >= 92 and urgency == "critical":
        return "critical"
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    if score >= 15:
        return "low"
    return "disqualify"


def classify_confidence(
    lead: LeadScoringRequest, score: int, missing_count: int
) -> str:
    if is_vague_message(lead.message):
        return "medium"
    if missing_count >= 2 and score >= 50:
        return "low"
    if score >= 75 and missing_count == 0:
        return "high"
    return "medium"


def classify_persona(role: str) -> str:
    role_value = normalize(role)
    if "vp of sales" in role_value:
        return "Sales leader"
    if "head of revenue operations" in role_value:
        return "Revenue operations leader"
    if "revenue operations" in role_value:
        return "Revenue operations"
    if "commercial operations" in role_value:
        return "Enterprise operations"
    if "founder" in role_value:
        return "Founder"
    if "marketing" in role_value:
        return "Marketing operator"
    return "General evaluator"


def detect_pain_points(message: str) -> list[str]:
    pain_points: list[str] = []
    checks = [
        (("qualifying inbound", "lead scoring", "bad fit leads"), "Lead qualification"),
        (("routing", "handoff", "route"), "Lead routing"),
        (("follow-up", "follow up"), "Follow-up automation"),
        (("crm cleanup", "cleaning fields", "crm hygiene"), "CRM cleanup"),
        (("inbound volume", "sdr queue", "reps"), "Rep workload"),
        (("sales operations", "sales ops", "sales admin"), "Sales operations"),
        (("implementation", "live before monday"), "Implementation urgency"),
        (("budget is tight", "budget"), "Budget sensitivity"),
    ]
    for keywords, label in checks:
        if contains_any(message, keywords):
            pain_points.append(label)
    return pain_points or ["Unclear need"]


def needs_human_review(
    lead: LeadScoringRequest, priority: Priority, confidence: str, missing_count: int
) -> bool:
    enterprise_size = normalize(lead.company_size) == "5000+"
    complex_or_urgent = normalize(lead.timeline) == "urgent" or contains_any(
        lead.message, ("implementation", "pricing", "legal", "live before monday")
    )
    return (
        priority == "critical"
        or confidence == "low"
        or (priority == "high" and normalize(lead.timeline) == "this_week")
        or (priority == "high" and normalize(lead.budget) == "approved")
        or (priority == "high" and complex_or_urgent)
        or (enterprise_size and missing_count > 0)
    )


def recommended_route(priority: Priority, persona: str, confidence: str) -> str:
    if priority == "critical":
        return "Immediate revenue operations and sales leadership route"
    if confidence == "low":
        return "Human review queue for qualification"
    if persona in {"Revenue operations", "Revenue operations leader"}:
        return "Revenue operations specialist"
    if persona == "Enterprise operations":
        return "Enterprise qualification review"
    if persona == "Founder":
        return "SMB sales route"
    if priority == "low":
        return "Nurture sequence"
    return "Sales AE route"


def next_best_action(priority: Priority, confidence: str, urgency: str) -> str:
    if priority == "critical":
        return "Respond same day and schedule urgent implementation discovery."
    if confidence == "low":
        return "Ask for missing timeline, budget, and use case details before routing."
    if priority == "high":
        return "Schedule discovery and confirm the main routing or scoring goal."
    if priority == "medium":
        return "Qualify budget, timeline, and workflow fit."
    if priority == "low":
        return "Send basic overview content and ask one qualifying question."
    return "Do not route to active sales follow-up."


def build_reasoning(reasons: list[str], priority: Priority, confidence: str) -> str:
    useful_reasons = [reason for reason in reasons if reason]
    summary = ", ".join(useful_reasons[:5])
    return (
        f"Priority is {priority} with {confidence} confidence based on {summary}."
        if summary
        else f"Priority is {priority} with {confidence} confidence based on limited signals."
    )
