import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config.settings import get_settings
from app.models.audit import AuditEventCreate
from app.models.hubspot import (
    HubSpotObjectIds,
    HubSpotPropertyDefinition,
    HubSpotPropertySetupResponse,
    HubSpotStatusResponse,
    HubSpotSyncResult,
)
from app.models.lead_intake import (
    CRMLeadRecord,
    LeadEnrichmentResult,
    LeadIntakeRequest,
)
from app.models.lead_scoring import LeadScoringResponse
from app.services.audit_trail import create_audit_event
from app.services.mock_crm_adapter import (
    append_crm_activity,
    full_name,
    get_lead_record_by_lead_id,
    get_lead_record_for_intake,
    upsert_record,
)
from app.services.workflow_steps import (
    log_step_failure,
    log_step_skipped,
    log_step_started,
    log_step_success,
)


WORKFLOW_NAME = "lead_intake_enrichment"
HUBSPOT_API_BASE_URL = "https://api.hubapi.com"
AI_PROPERTY_NAMES = [
    "ai_lead_score",
    "ai_priority",
    "ai_route",
    "ai_confidence",
    "ai_next_action",
    "ai_human_review_required",
    "ai_last_workflow_run",
    "ai_hygiene_score",
    "ai_risk_level",
    "ai_follow_up_status",
    "ai_proposal_status",
]
HUBSPOT_INDUSTRY_OPTIONS = {
    "software": "COMPUTER_SOFTWARE",
    "saas": "COMPUTER_SOFTWARE",
    "computer software": "COMPUTER_SOFTWARE",
    "technology": "INFORMATION_TECHNOLOGY_AND_SERVICES",
    "it services": "INFORMATION_TECHNOLOGY_AND_SERVICES",
    "marketing services": "MARKETING_AND_ADVERTISING",
    "marketing": "MARKETING_AND_ADVERTISING",
    "education": "EDUCATION_MANAGEMENT",
    "e-learning": "E_LEARNING",
    "elearning": "E_LEARNING",
    "financial services": "FINANCIAL_SERVICES",
    "healthcare": "HOSPITAL_HEALTH_CARE",
    "retail": "RETAIL",
    "consulting": "MANAGEMENT_CONSULTING",
}
HUBSPOT_INDUSTRY_VALUES = set(HUBSPOT_INDUSTRY_OPTIONS.values())
HUBSPOT_EMPLOYEE_RANGE_VALUES = {
    "1-10": "10",
    "11-50": "50",
    "51-200": "200",
    "51-500": "500",
    "201-500": "500",
    "501-1000": "1000",
    "1001-5000": "5000",
    "5000+": "5000",
}


class HubSpotAdapterError(RuntimeError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
        recommended_fix: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.recommended_fix = recommended_fix or recommended_fix_for_status(status_code)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_hubspot_status() -> HubSpotStatusResponse:
    settings = get_settings()
    token_configured = bool(settings.hubspot_access_token.strip())
    enabled = bool(settings.hubspot_enabled)
    adapter_mode = settings.crm_adapter_mode.strip().lower() or "mock"
    if adapter_mode != "hubspot" or not enabled:
        status = "disabled_mock_mode"
    elif not token_configured:
        status = "missing_token"
    else:
        status = "ready"
    return HubSpotStatusResponse(
        adapter_mode=adapter_mode,
        hubspot_enabled=enabled,
        token_configured=token_configured,
        portal_id=settings.hubspot_portal_id or None,
        default_pipeline_configured=bool(settings.hubspot_default_pipeline),
        default_deal_stage_configured=bool(settings.hubspot_default_deal_stage),
        owner_id_configured=bool(settings.hubspot_owner_id),
        status=status,
    )


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
    settings = get_settings()
    log_step_started(
        workflow_run_id,
        WORKFLOW_NAME,
        "crm_adapter_write_started",
        8,
        "lead",
        lead_id,
        {"adapter_mode": "hubspot", "crm_update_status": crm_update_status},
    )
    log_step_started(
        workflow_run_id,
        WORKFLOW_NAME,
        "hubspot_sync_started",
        8,
        "lead",
        lead_id,
    )
    write_hubspot_audit(
        workflow_run_id,
        "hubspot_sync_started",
        lead_id,
        request.email,
        human_review_required=human_review_required,
        metadata={"crm_update_status": crm_update_status},
    )

    try:
        if crm_update_status == "blocked_pending_review":
            return block_sensitive_sync(
                lead_id,
                request,
                enrichment,
                score,
                crm_update_status,
                human_review_required,
                risk_flags,
                workflow_run_id,
                settings.hubspot_portal_id,
            )

        validate_hubspot_enabled(settings)
        payloads = build_hubspot_payloads(
            request,
            enrichment,
            score,
            crm_update_status,
            human_review_required,
            risk_flags,
            workflow_run_id,
        )
        log_step_success(
            workflow_run_id,
            WORKFLOW_NAME,
            "hubspot_custom_properties_checked",
            8,
            "lead",
            lead_id,
            {"property_count": len(AI_PROPERTY_NAMES)},
        )

        contact_id = create_or_update_contact(payloads["contact"], request.email)
        write_hubspot_audit(
            workflow_run_id,
            "hubspot_contact_upserted",
            lead_id,
            contact_id,
            metadata={"email": request.email},
        )
        log_step_success(
            workflow_run_id,
            WORKFLOW_NAME,
            "hubspot_contact_search_or_create",
            8,
            "contact",
            contact_id,
        )

        company_id = create_or_update_company(payloads["company"], request)
        write_hubspot_audit(
            workflow_run_id,
            "hubspot_company_upserted",
            lead_id,
            company_id,
            metadata={"company": request.company},
        )
        log_step_success(
            workflow_run_id,
            WORKFLOW_NAME,
            "hubspot_company_search_or_create",
            8,
            "company",
            company_id,
        )

        deal_id = create_or_update_deal(payloads["deal"])
        write_hubspot_audit(
            workflow_run_id,
            "hubspot_deal_upserted",
            lead_id,
            deal_id,
            metadata={"dealname": payloads["deal"]["properties"]["dealname"]},
        )
        log_step_success(
            workflow_run_id,
            WORKFLOW_NAME,
            "hubspot_deal_create_or_update",
            8,
            "deal",
            deal_id,
        )

        optional_failures: list[str] = []
        task_id = None
        note_id = None

        try:
            task_id = create_task(payloads["task"])
            write_hubspot_audit(
                workflow_run_id,
                "hubspot_task_created",
                lead_id,
                task_id,
                metadata={"customer_facing": False},
            )
            log_step_success(
                workflow_run_id,
                WORKFLOW_NAME,
                "hubspot_task_create",
                8,
                "task",
                task_id,
            )
        except Exception as error:
            adapter_error = as_hubspot_error(error)
            failure_reason = f"optional task failed: {adapter_error}"
            optional_failures.append(failure_reason)
            write_hubspot_audit(
                workflow_run_id,
                "hubspot_optional_task_failed",
                lead_id,
                contact_id,
                human_review_required=human_review_required,
                metadata={
                    "status_code": adapter_error.status_code,
                    "retryable": adapter_error.retryable,
                    "recommended_fix": "Check HubSpot task payload required properties and scopes.",
                },
            )
            log_step_failure(
                workflow_run_id,
                WORKFLOW_NAME,
                "hubspot_task_create",
                adapter_error,
                step_order=8,
                entity_type="lead",
                entity_id=lead_id,
                failure_reason=failure_reason,
                retryable=adapter_error.retryable,
                recommended_fix="Check HubSpot task payload required properties and scopes.",
                severity="warning",
                metadata_json={"optional": True},
            )

        try:
            note_id = create_note(payloads["note"])
            write_hubspot_audit(
                workflow_run_id,
                "hubspot_note_created",
                lead_id,
                note_id,
                metadata={"customer_facing": False},
            )
            log_step_success(
                workflow_run_id,
                WORKFLOW_NAME,
                "hubspot_note_create",
                8,
                "note",
                note_id,
            )
        except Exception as error:
            adapter_error = as_hubspot_error(error)
            failure_reason = f"optional note failed: {adapter_error}"
            optional_failures.append(failure_reason)
            write_hubspot_audit(
                workflow_run_id,
                "hubspot_optional_note_failed",
                lead_id,
                contact_id,
                human_review_required=human_review_required,
                metadata={
                    "status_code": adapter_error.status_code,
                    "retryable": adapter_error.retryable,
                    "recommended_fix": "Check HubSpot note payload required properties and scopes.",
                },
            )
            log_step_failure(
                workflow_run_id,
                WORKFLOW_NAME,
                "hubspot_note_create",
                adapter_error,
                step_order=8,
                entity_type="lead",
                entity_id=lead_id,
                failure_reason=failure_reason,
                retryable=adapter_error.retryable,
                recommended_fix="Check HubSpot note payload required properties and scopes.",
                severity="warning",
                metadata_json={"optional": True},
            )

        try:
            associate_records(contact_id, company_id, deal_id, task_id, note_id)
            write_hubspot_audit(
                workflow_run_id,
                "hubspot_records_associated",
                lead_id,
                deal_id,
                metadata={
                    "contact_id": contact_id,
                    "company_id": company_id,
                    "task_id": task_id,
                    "note_id": note_id,
                },
            )
            log_step_success(
                workflow_run_id,
                WORKFLOW_NAME,
                "hubspot_associations_created",
                8,
                "lead",
                lead_id,
            )
        except Exception as error:
            adapter_error = as_hubspot_error(error)
            failure_reason = f"optional association failed: {adapter_error}"
            optional_failures.append(failure_reason)
            write_hubspot_audit(
                workflow_run_id,
                "hubspot_optional_association_failed",
                lead_id,
                deal_id,
                human_review_required=human_review_required,
                metadata={
                    "status_code": adapter_error.status_code,
                    "retryable": adapter_error.retryable,
                    "recommended_fix": "Check HubSpot association payloads and object permissions.",
                },
            )
            log_step_failure(
                workflow_run_id,
                WORKFLOW_NAME,
                "hubspot_associations_created",
                adapter_error,
                step_order=8,
                entity_type="lead",
                entity_id=lead_id,
                failure_reason=failure_reason,
                retryable=adapter_error.retryable,
                recommended_fix="Check HubSpot association payloads and object permissions.",
                severity="warning",
                metadata_json={"optional": True},
            )

        sync_status = hubspot_sync_status_for_optional_failures(optional_failures)
        sync_error = hubspot_sync_error_for_optional_failures(optional_failures)

        record = persist_synced_record(
            lead_id,
            request,
            enrichment,
            score,
            crm_update_status,
            human_review_required,
            risk_flags,
            workflow_run_id,
            HubSpotObjectIds(
                contact_id=contact_id,
                company_id=company_id,
                deal_id=deal_id,
                task_id=task_id,
                note_id=note_id,
            ),
            sync_status,
            sync_error,
            settings.hubspot_portal_id or None,
        )
        write_hubspot_audit(
            workflow_run_id,
            "hubspot_sync_completed",
            lead_id,
            record.crm_record_id,
            human_review_required=human_review_required,
            metadata={
                "hubspot_sync_status": sync_status,
                "optional_failures": optional_failures,
            },
        )
        log_step_success(
            workflow_run_id,
            WORKFLOW_NAME,
            "hubspot_sync_completed",
            8,
            "lead",
            lead_id,
            {"hubspot_sync_status": sync_status, "optional_failures": optional_failures},
        )
        log_step_success(
            workflow_run_id,
            WORKFLOW_NAME,
            "crm_adapter_write_completed",
            8,
            "lead",
            lead_id,
            {"adapter_mode": "hubspot", "crm_record_id": record.crm_record_id},
        )
        return record
    except Exception as error:
        adapter_error = as_hubspot_error(error)
        log_step_failure(
            workflow_run_id,
            WORKFLOW_NAME,
            "hubspot_sync_failed",
            adapter_error,
            step_order=8,
            entity_type="lead",
            entity_id=lead_id,
            failure_reason=str(adapter_error),
            retryable=adapter_error.retryable,
            recommended_fix=adapter_error.recommended_fix,
            metadata_json={"adapter_mode": "hubspot"},
        )
        write_hubspot_audit(
            workflow_run_id,
            "hubspot_sync_failed",
            lead_id,
            request.email,
            human_review_required=True,
            metadata={
                "status_code": adapter_error.status_code,
                "retryable": adapter_error.retryable,
                "recommended_fix": adapter_error.recommended_fix,
            },
        )
        raise RuntimeError(str(adapter_error)) from error


def block_sensitive_sync(
    lead_id: str,
    request: LeadIntakeRequest,
    enrichment: LeadEnrichmentResult,
    score: LeadScoringResponse,
    crm_update_status: str,
    human_review_required: bool,
    risk_flags: list[str],
    workflow_run_id: str,
    portal_id: str | None,
) -> CRMLeadRecord:
    record = persist_synced_record(
        lead_id,
        request,
        enrichment,
        score,
        crm_update_status,
        human_review_required,
        risk_flags,
        workflow_run_id,
        HubSpotObjectIds(),
        "blocked_pending_review",
        "Sensitive HubSpot routing or deal updates blocked pending human review.",
        portal_id or None,
    )
    append_crm_activity(
        record.crm_record_id,
        record.lead_id,
        "crm_update_blocked",
        "HubSpot sync blocked pending review",
        "Sensitive HubSpot update was blocked by the existing CRM update policy.",
        "blocked",
        workflow_run_id,
        {"adapter_mode": "hubspot"},
    )
    write_hubspot_audit(
        workflow_run_id,
        "hubspot_sync_blocked",
        lead_id,
        record.crm_record_id,
        guardrails=risk_flags,
        human_review_required=True,
        metadata={"hubspot_sync_status": "blocked_pending_review"},
    )
    log_step_skipped(
        workflow_run_id,
        WORKFLOW_NAME,
        "hubspot_sync_skipped",
        "HubSpot sync blocked pending human review by CRM update policy.",
        8,
        "lead",
        lead_id,
        {"hubspot_sync_status": "blocked_pending_review"},
    )
    log_step_success(
        workflow_run_id,
        WORKFLOW_NAME,
        "crm_adapter_write_completed",
        8,
        "lead",
        lead_id,
        {"adapter_mode": "hubspot", "crm_record_id": record.crm_record_id},
    )
    return record


def persist_synced_record(
    lead_id: str,
    request: LeadIntakeRequest,
    enrichment: LeadEnrichmentResult,
    score: LeadScoringResponse,
    crm_update_status: str,
    human_review_required: bool,
    risk_flags: list[str],
    workflow_run_id: str,
    object_ids: HubSpotObjectIds,
    hubspot_sync_status: str,
    hubspot_sync_error: str | None,
    hubspot_portal_id: str | None,
) -> CRMLeadRecord:
    existing = get_lead_record_by_lead_id(lead_id)
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
        adapter_mode="hubspot",
        hubspot_contact_id=object_ids.contact_id,
        hubspot_company_id=object_ids.company_id,
        hubspot_deal_id=object_ids.deal_id,
        hubspot_task_id=object_ids.task_id,
        hubspot_note_id=object_ids.note_id,
        hubspot_sync_status=hubspot_sync_status,
        hubspot_sync_error=hubspot_sync_error,
        last_hubspot_sync_at=utc_now(),
        hubspot_portal_id=hubspot_portal_id,
    )
    if hubspot_sync_status in {"synced", "partial_sync"}:
        append_crm_activity(
            record.crm_record_id,
            record.lead_id,
            "crm_update_applied",
            "HubSpot sync applied",
            f"Safe HubSpot sandbox sync completed with status {hubspot_sync_status}.",
            "applied",
            workflow_run_id,
            {"adapter_mode": "hubspot"},
        )
    return record


def validate_hubspot_enabled(settings) -> None:
    if not settings.hubspot_enabled:
        raise HubSpotAdapterError(
            "HubSpot is disabled; mock CRM mode should handle this request.",
            retryable=False,
            recommended_fix="Set HUBSPOT_ENABLED=true only when intentionally using the sandbox.",
        )
    if not settings.hubspot_access_token.strip():
        raise HubSpotAdapterError(
            "HubSpot access token is missing.",
            retryable=False,
            recommended_fix="Configure HUBSPOT_ACCESS_TOKEN for the HubSpot private app.",
        )


def build_hubspot_payloads(
    request: LeadIntakeRequest,
    enrichment: LeadEnrichmentResult,
    score: LeadScoringResponse,
    crm_update_status: str,
    human_review_required: bool,
    risk_flags: list[str],
    workflow_run_id: str,
) -> dict[str, dict]:
    settings = get_settings()
    contact_name = full_name(request)
    first_name = request.first_name or (contact_name.split(" ")[0] if contact_name else "")
    last_name = request.last_name or ""
    ai_properties = {
        "ai_lead_score": str(score.lead_score),
        "ai_priority": score.priority,
        "ai_route": score.recommended_route,
        "ai_confidence": score.confidence,
        "ai_next_action": score.next_best_action,
        "ai_human_review_required": str(human_review_required).lower(),
        "ai_last_workflow_run": workflow_run_id,
        "ai_risk_level": "high" if crm_update_status == "blocked_pending_review" else "medium" if human_review_required else "low",
    }
    contact_properties = {
        "email": request.email,
        "firstname": first_name,
        "lastname": last_name,
        "jobtitle": request.job_title or "",
        "company": request.company,
        "lifecyclestage": "lead",
        **ai_properties,
    }
    company_properties = {
        "name": request.company,
        "domain": domain_from_website(request.company_website) or domain_from_email(request.email),
        "website": request.company_website or "",
        "industry": normalize_hubspot_industry(
            request.industry or enrichment.industry_normalized
        ),
        "numberofemployees": normalize_hubspot_numberofemployees(
            request.company_size
        ),
        "ai_priority": score.priority,
        "ai_confidence": score.confidence,
        "ai_last_workflow_run": workflow_run_id,
        "ai_risk_level": ai_properties["ai_risk_level"],
    }
    deal_properties = {
        "dealname": f"{request.company} - Revenue AI lead intake",
        "pipeline": settings.hubspot_default_pipeline,
        "dealstage": settings.hubspot_default_deal_stage,
        "ai_priority": score.priority,
        "ai_route": score.recommended_route,
        "ai_confidence": score.confidence,
        "ai_next_action": score.next_best_action,
        "ai_human_review_required": str(human_review_required).lower(),
        "ai_last_workflow_run": workflow_run_id,
        "ai_risk_level": ai_properties["ai_risk_level"],
    }
    if settings.hubspot_owner_id:
        deal_properties["hubspot_owner_id"] = settings.hubspot_owner_id

    safe_summary = (
        f"Lead score {score.lead_score}, priority {score.priority}, "
        f"route {score.recommended_route}, confidence {score.confidence}. "
        f"Next action: {score.next_best_action}. "
        f"Human review required: {human_review_required}."
    )
    return {
        "contact": {"properties": compact_properties(contact_properties)},
        "company": {"properties": compact_properties(company_properties)},
        "deal": {"properties": compact_properties(deal_properties)},
        "task": {
            "properties": compact_properties(
                {
                    "hs_timestamp": hubspot_task_due_timestamp_ms(),
                    "hs_task_subject": f"Review new qualified lead: {request.company}",
                    "hs_task_body": score.next_best_action,
                    "hs_task_status": "NOT_STARTED",
                    "hs_task_priority": hubspot_task_priority(score.priority),
                    "hs_task_type": "TODO",
                    "hubspot_owner_id": settings.hubspot_owner_id,
                }
            )
        },
        "note": {
            "properties": {
                "hs_timestamp": hubspot_current_timestamp_ms(),
                "hs_note_body": safe_summary
                + f" Risk flags: {', '.join(risk_flags) if risk_flags else 'none'}."
            }
        },
    }


def create_or_update_contact(payload: dict, email: str) -> str:
    existing_id = search_object("contacts", "email", email)
    if existing_id:
        return patch_object("contacts", existing_id, payload)
    return create_object("contacts", payload)


def create_or_update_company(payload: dict, request: LeadIntakeRequest) -> str:
    domain = payload["properties"].get("domain") or domain_from_email(request.email)
    existing_id = search_object("companies", "domain", domain) if domain else None
    if existing_id:
        return patch_object("companies", existing_id, payload)
    return create_object("companies", payload)


def create_or_update_deal(payload: dict) -> str:
    return create_object("deals", payload)


def create_task(payload: dict) -> str:
    return create_object("tasks", payload)


def create_note(payload: dict) -> str:
    return create_object("notes", payload)


def associate_records(
    contact_id: str,
    company_id: str,
    deal_id: str,
    task_id: str | None,
    note_id: str | None,
) -> None:
    if not all([contact_id, company_id, deal_id]):
        raise HubSpotAdapterError(
            "Cannot associate core HubSpot records because one or more core object ids are missing.",
            retryable=False,
            recommended_fix="Check HubSpot contact, company, and deal creation responses before association.",
        )
    default_associations = [
        ("contacts", contact_id, "companies", company_id),
        ("deals", deal_id, "contacts", contact_id),
        ("deals", deal_id, "companies", company_id),
    ]
    if task_id:
        default_associations.append(("tasks", task_id, "contacts", contact_id))
    if note_id:
        default_associations.append(("notes", note_id, "contacts", contact_id))
    for from_type, from_id, to_type, to_id in default_associations:
        hubspot_request(
            "PUT",
            f"/crm/v4/objects/{from_type}/{from_id}/associations/default/{to_type}/{to_id}",
        )


def search_object(object_type: str, property_name: str, value: str) -> str | None:
    payload = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": property_name,
                        "operator": "EQ",
                        "value": value,
                    }
                ]
            }
        ],
        "limit": 1,
    }
    response = hubspot_request("POST", f"/crm/v3/objects/{object_type}/search", payload)
    results = response.get("results", [])
    return str(results[0]["id"]) if results else None


def create_object(object_type: str, payload: dict) -> str:
    response = hubspot_request("POST", f"/crm/v3/objects/{object_type}", payload)
    return str(response["id"])


def patch_object(object_type: str, object_id: str, payload: dict) -> str:
    response = hubspot_request("PATCH", f"/crm/v3/objects/{object_type}/{object_id}", payload)
    return str(response.get("id", object_id))


def ensure_custom_properties() -> HubSpotPropertySetupResponse:
    status = get_hubspot_status()
    if status.status != "ready":
        return HubSpotPropertySetupResponse(
            status=status.status,
            hubspot_enabled=status.hubspot_enabled,
            token_configured=status.token_configured,
        )

    created: list[str] = []
    skipped_existing: list[str] = []
    failed: list[str] = []
    failed_details: list[str] = []
    for definition in build_custom_property_definitions():
        property_reference = f"{definition.object_type}.{definition.name}"
        try:
            hubspot_request(
                "GET",
                f"/crm/v3/properties/{definition.object_type}/{definition.name}",
            )
            skipped_existing.append(property_reference)
        except HubSpotAdapterError as error:
            if error.status_code != 404:
                failed.append(property_reference)
                failed_details.append(f"{property_reference}: {safe_setup_error(error)}")
                continue
            try:
                property_payload = {
                    "name": definition.name,
                    "label": definition.label,
                    "type": definition.property_type,
                    "fieldType": definition.field_type,
                    "groupName": definition.group_name,
                }
                if definition.options:
                    property_payload["options"] = definition.options
                hubspot_request(
                    "POST",
                    f"/crm/v3/properties/{definition.object_type}",
                    property_payload,
                )
                created.append(property_reference)
            except HubSpotAdapterError as create_error:
                failed.append(property_reference)
                failed_details.append(
                    f"{property_reference}: {safe_setup_error(create_error)}"
                )
    return HubSpotPropertySetupResponse(
        status="completed" if not failed else "partial_failure",
        hubspot_enabled=True,
        token_configured=True,
        created=created,
        skipped_existing=skipped_existing,
        failed=failed,
        failed_details=failed_details,
    )


def build_custom_property_definitions() -> list[HubSpotPropertyDefinition]:
    labels = {
        "ai_lead_score": ("AI Lead Score", "number", "number"),
        "ai_priority": ("AI Priority", "text", "string"),
        "ai_route": ("AI Route", "text", "string"),
        "ai_confidence": ("AI Confidence", "text", "string"),
        "ai_next_action": ("AI Next Action", "textarea", "string"),
        "ai_human_review_required": ("AI Human Review Required", "select", "enumeration"),
        "ai_last_workflow_run": ("AI Last Workflow Run", "text", "string"),
        "ai_hygiene_score": ("AI Hygiene Score", "number", "number"),
        "ai_risk_level": ("AI Risk Level", "text", "string"),
        "ai_follow_up_status": ("AI Follow-Up Status", "text", "string"),
        "ai_proposal_status": ("AI Proposal Status", "text", "string"),
    }
    definitions: list[HubSpotPropertyDefinition] = []
    for object_type in ["contacts", "companies", "deals"]:
        group_name = "dealinformation" if object_type == "deals" else "contactinformation"
        if object_type == "companies":
            group_name = "companyinformation"
        for name in AI_PROPERTY_NAMES:
            label, field_type, property_type = labels[name]
            definitions.append(
                HubSpotPropertyDefinition(
                    object_type=object_type,
                    name=name,
                    label=label,
                    field_type=field_type,
                    property_type=property_type,
                    group_name=group_name,
                    options=human_review_required_options()
                    if name == "ai_human_review_required"
                    else [],
                )
            )
    return definitions


def human_review_required_options() -> list[dict]:
    return [
        {
            "label": "Yes",
            "value": "true",
            "displayOrder": 0,
            "hidden": False,
        },
        {
            "label": "No",
            "value": "false",
            "displayOrder": 1,
            "hidden": False,
        },
    ]


def safe_setup_error(error: HubSpotAdapterError) -> str:
    return str(error).replace("Bearer ", "Bearer [redacted] ")


def sync_lead_to_hubspot(lead_id: str) -> HubSpotSyncResult:
    status = get_hubspot_status()
    if status.status != "ready":
        return HubSpotSyncResult(
            status="not_enabled" if status.status == "disabled_mock_mode" else "failed",
            error=status.status,
            retryable=False,
            recommended_fix=(
                "Enable HubSpot mode and configure HUBSPOT_ACCESS_TOKEN before manual sync."
            ),
        )

    record = get_lead_record_for_intake(lead_id)
    request, enrichment, score = record_to_sync_context(record)
    synced_record = create_or_update_lead_record(
        lead_id=record.lead_id,
        request=request,
        enrichment=enrichment,
        score=score,
        crm_update_status=record.crm_update_status,
        human_review_required=record.human_review_required,
        risk_flags=record.risk_flags,
        workflow_run_id=str(record.metadata_json.get("workflow_run_id") or f"manual_sync:{lead_id}"),
    )
    return HubSpotSyncResult(
        status=synced_record.hubspot_sync_status,
        object_ids=HubSpotObjectIds(
            contact_id=synced_record.hubspot_contact_id,
            company_id=synced_record.hubspot_company_id,
            deal_id=synced_record.hubspot_deal_id,
            task_id=synced_record.hubspot_task_id,
            note_id=synced_record.hubspot_note_id,
        ),
        error=synced_record.hubspot_sync_error,
        metadata_json={"crm_record_id": synced_record.crm_record_id},
    )


def record_to_sync_context(
    record: CRMLeadRecord,
) -> tuple[LeadIntakeRequest, LeadEnrichmentResult, LeadScoringResponse]:
    request = LeadIntakeRequest(
        first_name=(record.contact_name or "").split(" ")[0] if record.contact_name else None,
        last_name=" ".join((record.contact_name or "").split(" ")[1:]) or None,
        email=record.email,
        company=record.company,
        job_title=record.enriched_persona,
        company_size=record.company_size_band,
        industry=record.industry_normalized,
        region=record.region_normalized,
        source=record.source,
        message=record.next_best_action,
        pain_points=[],
        urgency=record.urgency,
        budget_context="unknown",
        requested_demo=record.source == "demo_request",
        crm_system="HubSpot",
        notes="Manual HubSpot sync from local CRM record.",
    )
    enrichment = LeadEnrichmentResult(
        company_size_band=record.company_size_band,
        industry_normalized=record.industry_normalized,
        region_normalized=record.region_normalized,
        persona=record.enriched_persona,
        likely_team="unknown",
        lead_source_type=record.source,
        crm_match_status="hubspot_known",
        fit_notes=[],
        enrichment_confidence="medium" if record.risk_flags else "high",
        enrichment_risk_flags=record.risk_flags,
        buying_signals=[],
    )
    score = LeadScoringResponse(
        lead_id=record.lead_id,
        lead_score=record.lead_score,
        priority=record.priority,
        persona=record.enriched_persona,
        pain_points=[],
        urgency=record.urgency,
        recommended_route=record.recommended_route,
        next_best_action=record.next_best_action,
        confidence=record.confidence,
        human_review_required=record.human_review_required,
        reasoning="Manual HubSpot sync reused the existing local CRM record.",
    )
    return request, enrichment, score


def hubspot_request(method: str, path: str, payload: dict | None = None) -> dict:
    settings = get_settings()
    validate_hubspot_enabled(settings)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{HUBSPOT_API_BASE_URL}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {settings.hubspot_access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        safe_message = safe_hubspot_error_message(error)
        raise HubSpotAdapterError(
            safe_message,
            status_code=error.code,
            retryable=is_retryable_status(error.code),
            recommended_fix=recommended_fix_for_status(error.code),
        ) from error
    except urllib.error.URLError as error:
        raise HubSpotAdapterError(
            "HubSpot network request failed.",
            retryable=True,
            recommended_fix="Check network access and retry the sandbox sync.",
        ) from error


def safe_hubspot_error_message(error: urllib.error.HTTPError) -> str:
    try:
        body = error.read().decode("utf-8")
        parsed = json.loads(body)
        message = parsed.get("message") or parsed.get("error") or "HubSpot request failed."
    except Exception:
        message = "HubSpot request failed."
    return f"HubSpot request failed with status {error.code}: {message}"


def as_hubspot_error(error: Exception) -> HubSpotAdapterError:
    if isinstance(error, HubSpotAdapterError):
        return error
    return HubSpotAdapterError(
        str(error),
        retryable=True,
        recommended_fix="Check HubSpot sandbox sync inputs and retry if the issue was transient.",
    )


def is_retryable_status(status_code: int | None) -> bool:
    return status_code == 429 or bool(status_code and status_code >= 500)


def recommended_fix_for_status(status_code: int | None) -> str:
    if status_code in {401, 403}:
        return "Verify the HubSpot private app token and required CRM scopes."
    if status_code == 429:
        return "HubSpot rate limit hit; retry after backoff."
    if status_code and status_code >= 500:
        return "HubSpot returned a server error; retry later."
    if status_code == 400:
        return "Check HubSpot property payload mapping for standard and custom fields."
    if status_code == 404:
        return "Check the HubSpot object or property path."
    return "Check HubSpot configuration and request payload."


def write_hubspot_audit(
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
            event_source="hubspot_adapter",
            actor="system",
            output_reference=output_reference,
            guardrails_triggered=guardrails or [],
            human_review_required=human_review_required,
            metadata_json=metadata or {},
        )
    )


def compact_properties(properties: dict[str, Any]) -> dict[str, str]:
    return {
        key: str(value)
        for key, value in properties.items()
        if value is not None and str(value).strip()
    }


def normalize_hubspot_industry(value: str | None) -> str | None:
    normalized = " ".join(str(value or "").strip().split()).lower()
    if not normalized:
        return None
    hubspot_value = normalized.upper()
    if hubspot_value in HUBSPOT_INDUSTRY_VALUES:
        return hubspot_value
    return HUBSPOT_INDUSTRY_OPTIONS.get(normalized)


def normalize_hubspot_numberofemployees(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized.isdigit():
        return normalized
    return HUBSPOT_EMPLOYEE_RANGE_VALUES.get(normalized)


def hubspot_task_due_timestamp_ms() -> str:
    due_at = datetime.now(timezone.utc) + timedelta(hours=24)
    return str(int(due_at.timestamp() * 1000))


def hubspot_current_timestamp_ms() -> str:
    return str(int(datetime.now(timezone.utc).timestamp() * 1000))


def hubspot_task_priority(priority: str | None) -> str:
    normalized = str(priority or "").strip().lower()
    if normalized in {"critical", "high"}:
        return "HIGH"
    if normalized == "medium":
        return "MEDIUM"
    return "LOW"


def hubspot_sync_status_for_optional_failures(optional_failures: list[str]) -> str:
    return "partial_sync" if optional_failures else "synced"


def hubspot_sync_error_for_optional_failures(optional_failures: list[str]) -> str | None:
    return "; ".join(optional_failures) if optional_failures else None


def domain_from_email(email: str) -> str:
    return email.split("@")[-1].strip().lower() if "@" in email else ""


def domain_from_website(website: str | None) -> str:
    if not website:
        return ""
    cleaned = website.replace("https://", "").replace("http://", "").split("/")[0]
    return cleaned.strip().lower()
