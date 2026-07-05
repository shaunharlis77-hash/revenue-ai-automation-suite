from datetime import datetime, timezone
from uuid import uuid4

from app.models.audit import AuditEventCreate
from app.models.lead_intake import (
    CRMLeadRecord,
    LeadEnrichmentResult,
    LeadIntakeRequest,
)
from app.models.lead_scoring import LeadScoringResponse
from app.models.mock_crm import CRMActivity
from app.services.audit_trail import create_audit_event
from app.services.database import decode_json, encode_json, get_connection
from app.services.workflow_steps import (
    log_step_failure,
    log_step_started,
    log_step_success,
)


WORKFLOW_NAME = "lead_intake_enrichment"
DEMO_METADATA_KEY = "lead_intake"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_or_update_lead_record(
    lead_id: str,
    request: LeadIntakeRequest,
    enrichment: LeadEnrichmentResult,
    score: LeadScoringResponse,
    crm_update_status: str,
    human_review_required: bool,
    risk_flags: list[str],
    workflow_run_id: str,
) -> CRMLeadRecord:
    log_step_started(
        workflow_run_id,
        WORKFLOW_NAME,
        "crm_adapter_write_started",
        8,
        "lead",
        lead_id,
        {"crm_update_status": crm_update_status},
    )
    write_adapter_audit(
        workflow_run_id,
        "crm_adapter_write_started",
        lead_id,
        request.email,
        metadata={"crm_update_status": crm_update_status},
    )

    try:
        if should_simulate_adapter_failure(request):
            raise RuntimeError("Simulated mock CRM adapter write failure.")

        existing = get_lead_record_by_lead_id(lead_id)
        log_step_success(
            workflow_run_id,
            WORKFLOW_NAME,
            "crm_adapter_record_loaded",
            8,
            "lead",
            lead_id,
            {"record_found": existing is not None},
        )

        record = upsert_record(
            lead_id,
            request,
            enrichment,
            score,
            crm_update_status,
            human_review_required,
            risk_flags,
            workflow_run_id,
            existing,
        )
        log_step_success(
            workflow_run_id,
            WORKFLOW_NAME,
            "crm_adapter_record_created_or_updated",
            8,
            "lead",
            lead_id,
            {"crm_record_id": record.crm_record_id},
        )

        create_standard_activities(
            record,
            request,
            enrichment,
            score,
            crm_update_status,
            workflow_run_id,
        )

        event_type = (
            "crm_adapter_write_blocked"
            if crm_update_status == "blocked_pending_review"
            else "crm_adapter_write_applied"
        )
        write_adapter_audit(
            workflow_run_id,
            event_type,
            lead_id,
            record.crm_record_id,
            guardrails=risk_flags if crm_update_status == "blocked_pending_review" else [],
            human_review_required=human_review_required,
            metadata={
                "crm_record_id": record.crm_record_id,
                "crm_update_status": crm_update_status,
            },
        )
        log_step_success(
            workflow_run_id,
            WORKFLOW_NAME,
            "crm_adapter_write_completed",
            8,
            "lead",
            lead_id,
            {
                "crm_record_id": record.crm_record_id,
                "crm_update_status": crm_update_status,
            },
        )
        return record
    except Exception as error:
        log_step_failure(
            workflow_run_id,
            WORKFLOW_NAME,
            "crm_adapter_write_failed",
            error,
            step_order=8,
            entity_type="lead",
            entity_id=lead_id,
            failure_reason="Mock CRM adapter could not write the lead record.",
            retryable=True,
            recommended_fix=(
                "Check the mock CRM adapter database write path and retry the lead intake."
            ),
            metadata_json={"input_reference": request.email},
        )
        write_adapter_audit(
            workflow_run_id,
            "crm_adapter_write_failed",
            lead_id,
            request.email,
            human_review_required=True,
            metadata={"failure_reason": str(error)},
        )
        raise


def upsert_record(
    lead_id: str,
    request: LeadIntakeRequest,
    enrichment: LeadEnrichmentResult,
    score: LeadScoringResponse,
    crm_update_status: str,
    human_review_required: bool,
    risk_flags: list[str],
    workflow_run_id: str,
    existing: CRMLeadRecord | None,
) -> CRMLeadRecord:
    timestamp = utc_now()
    crm_record_id = existing.crm_record_id if existing else f"crm_lead_{uuid4()}"
    created_at = existing.created_at if existing else timestamp
    values = (
        crm_record_id,
        lead_id,
        request.company,
        full_name(request),
        request.email,
        request.source,
        enrichment.persona,
        enrichment.company_size_band,
        enrichment.industry_normalized,
        enrichment.region_normalized,
        score.lead_score,
        score.priority,
        score.confidence,
        score.urgency,
        score.recommended_route,
        score.next_best_action,
        crm_update_status,
        int(human_review_required),
        encode_json(risk_flags),
        created_at,
        timestamp,
        encode_json(
            {
                DEMO_METADATA_KEY: True,
                "workflow_run_id": workflow_run_id,
                "safe_internal_crm_record": True,
                "adapter": "mock_crm_adapter",
            }
        ),
    )
    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO crm_lead_records (
                    crm_record_id, lead_id, company, contact_name, email, source,
                    enriched_persona, company_size_band, industry_normalized,
                    region_normalized, lead_score, priority, confidence, urgency,
                    recommended_route, next_best_action, crm_update_status,
                    human_review_required, risk_flags, created_at, updated_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.commit()
    except Exception as error:
        raise RuntimeError(f"mock CRM record write failed: {error}") from error
    record = get_lead_record_by_lead_id(lead_id)
    if record is None:
        raise RuntimeError("mock CRM record write completed but the record could not be reloaded")
    return record


def create_standard_activities(
    record: CRMLeadRecord,
    request: LeadIntakeRequest,
    enrichment: LeadEnrichmentResult,
    score: LeadScoringResponse,
    crm_update_status: str,
    workflow_run_id: str,
) -> None:
    append_crm_activity(
        record.crm_record_id,
        record.lead_id,
        "lead_created",
        f"Lead record prepared for {record.company}",
        f"Internal CRM-style record created or updated from {request.source}.",
        "created",
        workflow_run_id,
    )
    append_crm_activity(
        record.crm_record_id,
        record.lead_id,
        "lead_enriched",
        "Lead enrichment completed",
        f"Persona {enrichment.persona} with {enrichment.enrichment_confidence} confidence.",
        "info",
        workflow_run_id,
    )
    append_crm_activity(
        record.crm_record_id,
        record.lead_id,
        "lead_scored",
        "Lead scoring completed",
        f"Score {score.lead_score}, priority {score.priority}, confidence {score.confidence}.",
        "info",
        workflow_run_id,
    )
    append_crm_activity(
        record.crm_record_id,
        record.lead_id,
        "route_assigned",
        "Recommended route assigned",
        score.recommended_route,
        "info",
        workflow_run_id,
    )

    if crm_update_status == "blocked_pending_review":
        append_crm_activity(
            record.crm_record_id,
            record.lead_id,
            "crm_update_blocked",
            "CRM update blocked pending review",
            "Sensitive routing or CRM changes were blocked until human review.",
            "blocked",
            workflow_run_id,
        )
        return

    append_crm_activity(
        record.crm_record_id,
        record.lead_id,
        "crm_update_applied",
        "Safe CRM update applied",
        f"Safe internal fields were written with status {crm_update_status}.",
        "applied",
        workflow_run_id,
    )
    if crm_update_status == "applied_with_review_visibility":
        append_crm_activity(
            record.crm_record_id,
            record.lead_id,
            "review_visibility_created",
            "Review visibility created",
            "The high-priority lead was updated immediately and flagged for review visibility.",
            "created",
            workflow_run_id,
        )


def append_crm_activity(
    crm_record_id: str,
    lead_id: str,
    activity_type: str,
    activity_title: str,
    activity_body: str,
    activity_status: str,
    workflow_run_id: str,
    metadata_json: dict | None = None,
) -> CRMActivity:
    crm_activity_id = f"crm_activity_{uuid4()}"
    created_at = utc_now()
    metadata = metadata_json or {}
    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO crm_activities (
                    crm_activity_id, crm_record_id, lead_id, activity_type,
                    activity_title, activity_body, activity_status,
                    source_workflow, workflow_run_id, created_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crm_activity_id,
                    crm_record_id,
                    lead_id,
                    activity_type,
                    activity_title,
                    activity_body,
                    activity_status,
                    WORKFLOW_NAME,
                    workflow_run_id,
                    created_at,
                    encode_json(metadata),
                ),
            )
            connection.commit()
    except Exception as error:
        raise RuntimeError(f"mock CRM activity write failed: {error}") from error

    activity = get_crm_activity(crm_activity_id)
    log_step_success(
        workflow_run_id,
        WORKFLOW_NAME,
        "crm_adapter_activity_created",
        8,
        "lead",
        lead_id,
        {"activity_type": activity_type, "crm_activity_id": crm_activity_id},
    )
    write_adapter_audit(
        workflow_run_id,
        "crm_activity_created",
        lead_id,
        crm_activity_id,
        metadata={"activity_type": activity_type, "crm_record_id": crm_record_id},
    )
    return activity


def get_lead_records() -> list[CRMLeadRecord]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM crm_lead_records ORDER BY updated_at DESC, id DESC"
        ).fetchall()
    return [crm_lead_record_from_row(row) for row in rows]


def get_lead_record(crm_record_id: str) -> CRMLeadRecord:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM crm_lead_records WHERE crm_record_id = ?",
            (crm_record_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"CRM lead record not found: {crm_record_id}")
    return crm_lead_record_from_row(row)


def get_lead_record_by_lead_id(lead_id: str) -> CRMLeadRecord | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM crm_lead_records WHERE lead_id = ?",
            (lead_id,),
        ).fetchone()
    return crm_lead_record_from_row(row) if row else None


def get_lead_record_for_intake(lead_id: str) -> CRMLeadRecord:
    record = get_lead_record_by_lead_id(lead_id)
    if record is None:
        raise ValueError(f"lead CRM record not found: {lead_id}")
    return record


def get_lead_record_activities(crm_record_id: str) -> list[CRMActivity]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM crm_activities
            WHERE crm_record_id = ?
            ORDER BY id ASC
            """,
            (crm_record_id,),
        ).fetchall()
    return [crm_activity_from_row(row) for row in rows]


def get_crm_activity(crm_activity_id: str) -> CRMActivity:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM crm_activities WHERE crm_activity_id = ?",
            (crm_activity_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"CRM activity not found: {crm_activity_id}")
    return crm_activity_from_row(row)


def crm_lead_record_from_row(row) -> CRMLeadRecord:
    return CRMLeadRecord(
        id=row["id"],
        crm_record_id=row["crm_record_id"],
        lead_id=row["lead_id"],
        company=row["company"],
        contact_name=row["contact_name"],
        email=row["email"],
        source=row["source"],
        enriched_persona=row["enriched_persona"],
        company_size_band=row["company_size_band"],
        industry_normalized=row["industry_normalized"],
        region_normalized=row["region_normalized"],
        lead_score=row["lead_score"],
        priority=row["priority"],
        confidence=row["confidence"],
        urgency=row["urgency"],
        recommended_route=row["recommended_route"],
        next_best_action=row["next_best_action"],
        crm_update_status=row["crm_update_status"],
        human_review_required=bool(row["human_review_required"]),
        risk_flags=decode_json(row["risk_flags"], []),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        metadata_json=decode_json(row["metadata_json"], {}),
    )


def crm_activity_from_row(row) -> CRMActivity:
    return CRMActivity(
        id=row["id"],
        crm_activity_id=row["crm_activity_id"],
        crm_record_id=row["crm_record_id"],
        lead_id=row["lead_id"],
        activity_type=row["activity_type"],
        activity_title=row["activity_title"],
        activity_body=row["activity_body"],
        activity_status=row["activity_status"],
        source_workflow=row["source_workflow"],
        workflow_run_id=row["workflow_run_id"],
        created_at=row["created_at"],
        metadata_json=decode_json(row["metadata_json"], {}),
    )


def write_adapter_audit(
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
            event_source="mock_crm_adapter",
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


def should_simulate_adapter_failure(request: LeadIntakeRequest) -> bool:
    text = " ".join(
        [
            request.email or "",
            request.company or "",
            request.message or "",
            request.notes or "",
        ]
    ).lower()
    return (
        "simulate_crm_adapter_failure" in text
        or "simulate_crm_failure" in text
    )
