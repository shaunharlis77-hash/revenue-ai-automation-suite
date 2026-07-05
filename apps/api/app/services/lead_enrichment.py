from app.models.lead_intake import LeadEnrichmentResult, LeadIntakeRequest


SUSPICIOUS_SIGNALS = ("test", "student", "school assignment", "please ignore", "asdf")
MISSING_VALUES = {"", "unknown", "none", "n/a", "na", "not_set"}


def enrich_lead(request: LeadIntakeRequest) -> LeadEnrichmentResult:
    if contains_any(combined_text(request), ("simulate_enrichment_failure",)):
        raise RuntimeError("Simulated enrichment failure.")

    risk_flags: list[str] = []
    fit_notes: list[str] = []
    buying_signals: list[str] = []

    company_size_band = normalize_company_size(request.company_size)
    industry_normalized = normalize_text_value(request.industry, "unknown")
    region_normalized = normalize_text_value(request.region, "unknown")
    persona = infer_persona(request.job_title)
    likely_team = infer_likely_team(persona)
    lead_source_type = infer_source_type(request.source, request.requested_demo)
    crm_match_status = infer_crm_match_status(request.crm_system)

    if company_size_band == "unknown":
        risk_flags.append("missing_company_size")
    else:
        fit_notes.append(f"Company size appears to be {company_size_band}.")

    if persona == "general_evaluator":
        fit_notes.append("Role has limited buying authority signal.")
    else:
        fit_notes.append(f"Persona inferred as {persona}.")

    if request.requested_demo or contains_any(combined_text(request), ("demo",)):
        buying_signals.append("demo_requested")
    if contains_any(combined_text(request), ("urgent", "this week", "immediate")):
        buying_signals.append("urgent_timing")
    if contains_any(combined_text(request), ("approved budget", "budget approved")):
        buying_signals.append("approved_budget")
    if contains_any(combined_text(request), ("routing", "lead scoring", "inbound", "crm cleanup")):
        buying_signals.append("sales_ops_pain")

    if contains_any(combined_text(request), SUSPICIOUS_SIGNALS):
        risk_flags.append("suspicious_or_test_submission")
    if not request.company_website:
        risk_flags.append("missing_company_website")
    if industry_normalized == "unknown":
        risk_flags.append("missing_industry")

    enrichment_confidence = classify_confidence(risk_flags, company_size_band, persona)

    return LeadEnrichmentResult(
        company_size_band=company_size_band,
        industry_normalized=industry_normalized,
        region_normalized=region_normalized,
        persona=persona,
        likely_team=likely_team,
        lead_source_type=lead_source_type,
        crm_match_status=crm_match_status,
        fit_notes=fit_notes,
        enrichment_confidence=enrichment_confidence,
        enrichment_risk_flags=risk_flags,
        buying_signals=buying_signals,
    )


def combined_text(request: LeadIntakeRequest) -> str:
    return " ".join(
        [
            request.first_name or "",
            request.last_name or "",
            request.email,
            request.company,
            request.job_title or "",
            request.source,
            request.message or "",
            " ".join(request.pain_points),
            request.urgency or "",
            request.budget_context or "",
            request.crm_system or "",
            request.notes or "",
        ]
    ).lower()


def normalize(value: str | None) -> str:
    return str(value or "").strip().lower()


def normalize_text_value(value: str | None, fallback: str) -> str:
    normalized = normalize(value).replace(" ", "_").replace("-", "_")
    return fallback if normalized in MISSING_VALUES else normalized


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def normalize_company_size(company_size: str | None) -> str:
    size = normalize(company_size)
    if size in MISSING_VALUES:
        return "unknown"
    if size in {"1-10", "1_10", "1 to 10"}:
        return "small_business"
    if size in {"11-50", "11_50", "11 to 50"}:
        return "small_business"
    if size in {"51-200", "51_200", "51 to 200", "201-500", "201_500", "201 to 500"}:
        return "mid_market"
    if size in {"501-1000", "501_1000", "501 to 1000", "1001-5000", "5000+"}:
        return "enterprise"
    return "unknown"


def infer_persona(job_title: str | None) -> str:
    title = normalize(job_title)
    if any(term in title for term in ("head of sales", "vp of sales", "chief revenue", "revenue")):
        return "sales_leader"
    if any(term in title for term in ("growth", "marketing")):
        return "growth_leader"
    if any(term in title for term in ("revops", "revenue operations", "sales operations", "commercial operations")):
        return "revenue_operations"
    if "founder" in title or "ceo" in title:
        return "founder"
    return "general_evaluator"


def infer_likely_team(persona: str) -> str:
    teams = {
        "sales_leader": "sales",
        "growth_leader": "growth",
        "revenue_operations": "revenue_operations",
        "founder": "leadership",
    }
    return teams.get(persona, "unknown")


def infer_source_type(source: str, requested_demo: bool) -> str:
    normalized_source = normalize(source)
    if requested_demo or "demo" in normalized_source:
        return "high_intent_inbound"
    if "pricing" in normalized_source:
        return "commercial_intent"
    if "referral" in normalized_source:
        return "referral"
    return "general_inbound"


def infer_crm_match_status(crm_system: str | None) -> str:
    crm = normalize(crm_system)
    if crm == "hubspot":
        return "hubspot_known"
    if crm == "salesforce":
        return "salesforce_known"
    if crm == "pipedrive":
        return "pipedrive_known"
    if crm in MISSING_VALUES:
        return "crm_unknown"
    return "crm_other"


def classify_confidence(
    risk_flags: list[str], company_size_band: str, persona: str
) -> str:
    if "suspicious_or_test_submission" in risk_flags:
        return "low"
    if company_size_band == "unknown" and persona == "general_evaluator":
        return "low"
    if risk_flags:
        return "medium"
    return "high"
