import os
import sys
from pathlib import Path
from uuid import uuid4


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.config.settings import get_settings  # noqa: E402
from app.models.hubspot import HubSpotObjectIds  # noqa: E402
from app.models.lead_intake import LeadIntakeRequest  # noqa: E402
from app.services.hubspot_adapter import (  # noqa: E402
    HubSpotAdapterError,
    build_custom_property_definitions,
    build_hubspot_payloads,
    hubspot_sync_error_for_optional_failures,
    hubspot_sync_status_for_optional_failures,
    hubspot_task_priority,
    is_retryable_status,
    normalize_hubspot_industry,
    normalize_hubspot_numberofemployees,
    recommended_fix_for_status,
)
from app.services.lead_enrichment import enrich_lead  # noqa: E402
from app.services.lead_intake import build_scoring_request, evaluate_crm_update  # noqa: E402
from app.services.lead_scoring import _score_lead  # noqa: E402


TEST_RUN_ID = uuid4().hex[:8]
BANNED_CUSTOMER_SEND_FIELDS = ["email_body", "message_body", "send_email", "send_whatsapp"]


def main() -> int:
    set_mapping_env()
    checks = [
        ("HubSpot payload mapping contains safe CRM fields", check_payload_mapping),
        ("HubSpot standard company fields are normalized", check_company_standard_field_mapping),
        ("HubSpot task payload is valid and optional failures preserve core ids", check_task_payload_and_optional_sync),
        ("custom AI property definitions are complete", check_custom_property_definitions),
        ("guardrail behavior maps clean high and risky leads correctly", check_guardrail_mapping),
        ("HubSpot failure classification is observable", check_failure_classification),
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


def check_payload_mapping() -> None:
    request = high_priority_lead()
    enrichment = enrich_lead(request)
    score = _score_lead(build_scoring_request(f"lead_{TEST_RUN_ID}", request))
    decision = evaluate_crm_update(enrichment, score)
    payloads = build_hubspot_payloads(
        request,
        enrichment,
        score,
        decision["status"],
        decision["review_required"],
        decision["risk_flags"],
        f"workflow_{TEST_RUN_ID}",
    )

    contact = payloads["contact"]["properties"]
    company = payloads["company"]["properties"]
    deal = payloads["deal"]["properties"]
    task = payloads["task"]["properties"]
    note = payloads["note"]["properties"]

    assert contact["email"] == request.email
    assert contact["firstname"] == "Maya"
    assert contact["lastname"] == "Chen"
    assert company["name"] == request.company
    assert company["domain"] == "northstar-analytics-demo.com"
    assert company["numberofemployees"] == "500"
    assert "industry" not in company
    assert deal["pipeline"] == "default"
    assert deal["dealstage"] == "appointmentscheduled"
    assert deal["ai_priority"] in {"high", "critical"}
    assert deal["ai_route"] == score.recommended_route
    assert contact["ai_human_review_required"] == "true"
    assert deal["ai_human_review_required"] == "true"
    assert task["hs_task_body"] == score.next_best_action
    assert task["hs_timestamp"].isdigit()
    assert task["hs_task_subject"] == "Review new qualified lead: Northstar Analytics"
    assert task["hs_task_status"] == "NOT_STARTED"
    assert task["hs_task_priority"] == "HIGH"
    assert task["hs_task_type"] == "TODO"
    assert "hubspot_owner_id" not in task
    assert "Lead score" in note["hs_note_body"]
    flattened = str(payloads)
    for banned_field in BANNED_CUSTOMER_SEND_FIELDS:
        assert banned_field not in flattened, f"payload should not include {banned_field}"

    clean_request = clean_lead()
    clean_enrichment = enrich_lead(clean_request)
    clean_score = _score_lead(build_scoring_request(f"lead_clean_{TEST_RUN_ID}", clean_request))
    clean_decision = evaluate_crm_update(clean_enrichment, clean_score)
    clean_payloads = build_hubspot_payloads(
        clean_request,
        clean_enrichment,
        clean_score,
        clean_decision["status"],
        clean_decision["review_required"],
        clean_decision["risk_flags"],
        f"workflow_clean_{TEST_RUN_ID}",
    )
    assert clean_payloads["contact"]["properties"]["ai_human_review_required"] == "false"
    assert clean_payloads["deal"]["properties"]["ai_human_review_required"] == "false"
    assert clean_payloads["company"]["properties"]["industry"] == "MARKETING_AND_ADVERTISING"
    assert clean_payloads["company"]["properties"]["numberofemployees"] == "200"


def check_company_standard_field_mapping() -> None:
    assert normalize_hubspot_industry("Software") == "COMPUTER_SOFTWARE"
    assert normalize_hubspot_industry("COMPUTER_SOFTWARE") == "COMPUTER_SOFTWARE"
    assert normalize_hubspot_industry("software") == "COMPUTER_SOFTWARE"
    assert normalize_hubspot_industry("SaaS") == "COMPUTER_SOFTWARE"
    assert normalize_hubspot_industry("Computer Software") == "COMPUTER_SOFTWARE"
    assert normalize_hubspot_industry("Technology") == "INFORMATION_TECHNOLOGY_AND_SERVICES"
    assert normalize_hubspot_industry("IT Services") == "INFORMATION_TECHNOLOGY_AND_SERVICES"
    assert normalize_hubspot_industry("Marketing Services") == "MARKETING_AND_ADVERTISING"
    assert normalize_hubspot_industry("Marketing") == "MARKETING_AND_ADVERTISING"
    assert normalize_hubspot_industry("Education") == "EDUCATION_MANAGEMENT"
    assert normalize_hubspot_industry("E-learning") == "E_LEARNING"
    assert normalize_hubspot_industry("Financial Services") == "FINANCIAL_SERVICES"
    assert normalize_hubspot_industry("Healthcare") == "HOSPITAL_HEALTH_CARE"
    assert normalize_hubspot_industry("Retail") == "RETAIL"
    assert normalize_hubspot_industry("Consulting") == "MANAGEMENT_CONSULTING"
    assert normalize_hubspot_industry("Analytics") is None

    assert normalize_hubspot_numberofemployees("1-10") == "10"
    assert normalize_hubspot_numberofemployees("11-50") == "50"
    assert normalize_hubspot_numberofemployees("51-200") == "200"
    assert normalize_hubspot_numberofemployees("51-500") == "500"
    assert normalize_hubspot_numberofemployees("201-500") == "500"
    assert normalize_hubspot_numberofemployees("501-1000") == "1000"
    assert normalize_hubspot_numberofemployees("1001-5000") == "5000"
    assert normalize_hubspot_numberofemployees("5000+") == "5000"
    assert normalize_hubspot_numberofemployees("275") == "275"
    assert normalize_hubspot_numberofemployees("unknown") is None

    unknown_request = clean_lead()
    unknown_request.industry = "Analytics"
    unknown_request.company_size = "unknown"
    unknown_enrichment = enrich_lead(unknown_request)
    unknown_score = _score_lead(
        build_scoring_request(f"lead_unknown_{TEST_RUN_ID}", unknown_request)
    )
    unknown_decision = evaluate_crm_update(unknown_enrichment, unknown_score)
    unknown_payloads = build_hubspot_payloads(
        unknown_request,
        unknown_enrichment,
        unknown_score,
        unknown_decision["status"],
        unknown_decision["review_required"],
        unknown_decision["risk_flags"],
        f"workflow_unknown_{TEST_RUN_ID}",
    )
    unknown_company = unknown_payloads["company"]["properties"]
    assert "industry" not in unknown_company
    assert "numberofemployees" not in unknown_company


def check_task_payload_and_optional_sync() -> None:
    assert hubspot_task_priority("critical") == "HIGH"
    assert hubspot_task_priority("high") == "HIGH"
    assert hubspot_task_priority("medium") == "MEDIUM"
    assert hubspot_task_priority("low") == "LOW"
    assert hubspot_task_priority("disqualify") == "LOW"
    assert hubspot_task_priority("unknown") == "LOW"

    optional_failures = ["optional task failed: required property missing"]
    object_ids = HubSpotObjectIds(
        contact_id="contact_123",
        company_id="company_123",
        deal_id="deal_123",
        task_id=None,
        note_id="note_123",
    )
    assert hubspot_sync_status_for_optional_failures(optional_failures) == "partial_sync"
    assert hubspot_sync_error_for_optional_failures(optional_failures) == optional_failures[0]
    assert object_ids.contact_id == "contact_123"
    assert object_ids.company_id == "company_123"
    assert object_ids.deal_id == "deal_123"
    assert object_ids.task_id is None


def check_custom_property_definitions() -> None:
    definitions = build_custom_property_definitions()
    names_by_object = {}
    definitions_by_reference = {}
    for definition in definitions:
        names_by_object.setdefault(definition.object_type, set()).add(definition.name)
        definitions_by_reference[f"{definition.object_type}.{definition.name}"] = definition

    for object_type in ["contacts", "companies", "deals"]:
        assert "ai_lead_score" in names_by_object[object_type]
        assert "ai_priority" in names_by_object[object_type]
        assert "ai_route" in names_by_object[object_type]
        assert "ai_confidence" in names_by_object[object_type]
        assert "ai_next_action" in names_by_object[object_type]
        assert "ai_human_review_required" in names_by_object[object_type]
        assert "ai_last_workflow_run" in names_by_object[object_type]
        assert "ai_risk_level" in names_by_object[object_type]
        review_definition = definitions_by_reference[
            f"{object_type}.ai_human_review_required"
        ]
        assert review_definition.property_type == "enumeration"
        assert review_definition.field_type == "select"
        assert review_definition.options == [
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


def check_guardrail_mapping() -> None:
    clean_decision = decision_for(clean_lead())
    high_decision = decision_for(high_priority_lead())
    risky_decision = decision_for(risky_lead())

    assert clean_decision["status"] == "applied", clean_decision
    assert clean_decision["review_required"] is False, clean_decision
    assert high_decision["status"] == "applied_with_review_visibility", high_decision
    assert high_decision["review_required"] is True, high_decision
    assert risky_decision["status"] == "blocked_pending_review", risky_decision
    assert risky_decision["review_required"] is True, risky_decision


def check_failure_classification() -> None:
    assert recommended_fix_for_status(401) == "Verify the HubSpot private app token and required CRM scopes."
    assert recommended_fix_for_status(403) == "Verify the HubSpot private app token and required CRM scopes."
    assert recommended_fix_for_status(429) == "HubSpot rate limit hit; retry after backoff."
    assert recommended_fix_for_status(500) == "HubSpot returned a server error; retry later."
    assert recommended_fix_for_status(400) == "Check HubSpot property payload mapping for standard and custom fields."
    assert is_retryable_status(429) is True
    assert is_retryable_status(503) is True
    assert is_retryable_status(401) is False
    error = HubSpotAdapterError("validation failed", status_code=400)
    assert error.retryable is False
    assert "property payload mapping" in error.recommended_fix


def decision_for(request: LeadIntakeRequest) -> dict:
    enrichment = enrich_lead(request)
    score = _score_lead(build_scoring_request(f"lead_{uuid4()}", request))
    return evaluate_crm_update(enrichment, score)


def clean_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Nadia",
        last_name="Patel",
        email=f"nadia.patel.{TEST_RUN_ID}@localgrowth-demo.com",
        company="Local Growth Studio",
        job_title="Operations Manager",
        company_website="https://localgrowth-demo.com",
        company_size="51-200",
        industry="Marketing Services",
        region="EMEA",
        source="webinar",
        message="We are evaluating CRM cleanup for our sales team and gathering options.",
        pain_points=["CRM cleanup"],
        urgency="60_days",
        budget_context="Planned budget",
        requested_demo=False,
        crm_system="HubSpot",
        notes="HubSpot mapping clean case.",
    )


def high_priority_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Maya",
        last_name="Chen",
        email=f"maya.chen.{TEST_RUN_ID}@northstar-analytics-demo.com",
        company="Northstar Analytics",
        job_title="VP of Sales",
        company_website="https://northstar-analytics-demo.com",
        company_size="201-500",
        industry="Analytics",
        region="North America",
        source="demo_request",
        message=(
            "We want a demo this week. Our reps are spending too much time "
            "qualifying inbound leads and we need better routing before launch."
        ),
        pain_points=["Lead routing", "Inbound volume", "Manual qualification"],
        urgency="this_week",
        budget_context="Approved budget",
        requested_demo=True,
        crm_system="HubSpot",
        notes="HubSpot mapping high priority case.",
    )


def risky_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Test",
        last_name="User",
        email=f"student.test.{TEST_RUN_ID}@example.com",
        company="Unknown Co",
        job_title="Student",
        company_size="unknown",
        industry="",
        region="",
        source="contact_form",
        message="This is for a school assignment, please ignore.",
        pain_points=["unclear need"],
        urgency="unknown",
        budget_context="unknown",
        requested_demo=False,
        crm_system="unknown",
        notes="HubSpot mapping risky case.",
    )


def set_mapping_env() -> None:
    os.environ["CRM_ADAPTER_MODE"] = "hubspot"
    os.environ["HUBSPOT_ENABLED"] = "true"
    os.environ["HUBSPOT_ACCESS_TOKEN"] = "not-a-real-token"
    os.environ["HUBSPOT_DEFAULT_PIPELINE"] = "default"
    os.environ["HUBSPOT_DEFAULT_DEAL_STAGE"] = "appointmentscheduled"
    os.environ["HUBSPOT_OWNER_ID"] = ""
    get_settings.cache_clear()


if __name__ == "__main__":
    raise SystemExit(main())
