export type ReviewItem = {
  review_item_id: string;
  workflow_run_id?: string | null;
  workflow_name: string;
  entity_type: string;
  entity_id: string;
  company?: string | null;
  contact_name?: string | null;
  review_type: string;
  title: string;
  status: "pending" | "approved" | "rejected";
  priority: string;
  risk_level: string;
  review_reasons: string[];
  proposed_action: string;
  proposed_output?: string | null;
  decision?: string | null;
  decision_reason?: string | null;
  assigned_to?: string | null;
  created_at: string;
  updated_at: string;
  metadata_json: Record<string, unknown>;
};

export type AuditEvent = {
  event_id: string;
  workflow_run_id?: string | null;
  workflow_name: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  event_source: string;
  actor: string;
  input_reference?: string | null;
  output_reference?: string | null;
  guardrails_triggered: string[];
  human_review_required: boolean;
  decision?: string | null;
  decision_reason?: string | null;
  created_at: string;
  metadata_json: Record<string, unknown>;
};

export type WorkflowStepEvent = {
  id?: number | null;
  step_event_id: string;
  workflow_run_id: string;
  workflow_name: string;
  step_name: string;
  step_status: "started" | "success" | "failed" | "skipped";
  step_order?: number | null;
  entity_type?: string | null;
  entity_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  severity: "info" | "warning" | "error" | "critical";
  error_type?: string | null;
  error_message?: string | null;
  failure_reason?: string | null;
  retryable: boolean;
  recommended_fix?: string | null;
  created_at: string;
  metadata_json: Record<string, unknown>;
};

export type LeadIntakeRequest = {
  first_name?: string | null;
  last_name?: string | null;
  email: string;
  company: string;
  job_title?: string | null;
  company_website?: string | null;
  company_size?: string | null;
  industry?: string | null;
  region?: string | null;
  source: string;
  message?: string | null;
  pain_points: string[];
  urgency?: string | null;
  budget_context?: string | null;
  requested_demo: boolean;
  crm_system?: string | null;
  notes?: string | null;
};

export type CRMLeadRecord = {
  crm_record_id: string;
  lead_id: string;
  company: string;
  contact_name?: string | null;
  email: string;
  source: string;
  enriched_persona: string;
  company_size_band: string;
  industry_normalized: string;
  region_normalized: string;
  lead_score: number;
  priority: string;
  confidence: string;
  urgency: string;
  recommended_route: string;
  next_best_action: string;
  crm_update_status:
    | "applied"
    | "blocked_pending_review"
    | "applied_with_review_visibility";
  human_review_required: boolean;
  risk_flags: string[];
  created_at: string;
  updated_at: string;
  metadata_json: Record<string, unknown>;
};

export type CRMActivity = {
  crm_activity_id: string;
  crm_record_id: string;
  lead_id: string;
  activity_type:
    | "lead_created"
    | "lead_enriched"
    | "lead_scored"
    | "route_assigned"
    | "crm_update_applied"
    | "crm_update_blocked"
    | "review_visibility_created";
  activity_title: string;
  activity_body: string;
  activity_status: "created" | "applied" | "blocked" | "info";
  source_workflow: string;
  workflow_run_id: string;
  created_at: string;
  metadata_json: Record<string, unknown>;
};

export type LeadIntakeResponse = {
  lead_id: string;
  crm_record: CRMLeadRecord;
  enrichment: {
    company_size_band: string;
    industry_normalized: string;
    region_normalized: string;
    persona: string;
    likely_team: string;
    lead_source_type: string;
    crm_match_status: string;
    fit_notes: string[];
    enrichment_confidence: "high" | "medium" | "low";
    enrichment_risk_flags: string[];
    buying_signals: string[];
  };
  lead_score: number;
  priority: string;
  confidence: string;
  urgency: string;
  recommended_route: string;
  next_best_action: string;
  crm_update_status: CRMLeadRecord["crm_update_status"];
  review_created: boolean;
  review_reasons: string[];
  workflow_run_id: string;
  reasoning: string;
};

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
}

export async function getReviewItems() {
  return getJson<ReviewItem[]>("/review/items");
}

export async function getAuditEvents() {
  const events = await getJson<AuditEvent[]>("/audit/events");
  return [...events].reverse();
}

export async function getWorkflowStepEvents() {
  const events = await getJson<WorkflowStepEvent[]>("/logs/workflow-steps");
  return [...events].reverse();
}

export async function submitLeadIntake(request: LeadIntakeRequest) {
  return postJson<LeadIntakeResponse>("/intake/lead", request);
}

export async function getLeadIntakeRecord(leadId: string) {
  return getJson<CRMLeadRecord>(`/intake/leads/${leadId}`);
}

export async function getCRMLeadRecords() {
  return getJson<CRMLeadRecord[]>("/crm/leads");
}

export async function getCRMLeadRecordActivities(crmRecordId: string) {
  return getJson<CRMActivity[]>(`/crm/leads/${crmRecordId}/activities`);
}

export async function decideReviewItem(
  reviewItemId: string,
  decision: "approve" | "reject",
  decisionReason: string,
) {
  return postJson<ReviewItem>(`/review/items/${reviewItemId}/${decision}`, {
    actor: "sales_manager",
    decision_reason: decisionReason,
  });
}

async function getJson<T>(path: string) {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown) {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}
