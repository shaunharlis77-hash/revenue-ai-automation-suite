import { redirect } from "next/navigation";

import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import {
  getLeadIntakeRecord,
  submitLeadIntake,
  type CRMLeadRecord,
  type LeadIntakeRequest,
} from "@/lib/api";

type LeadIntakePageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function LeadIntakePage({
  searchParams,
}: LeadIntakePageProps) {
  const params = searchParams ? await searchParams : {};
  const leadId = textParam(params.lead_id);
  const error = textParam(params.error);
  const { record, loadError } = leadId
    ? await loadLeadRecord(leadId)
    : { record: null, loadError: "" };

  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Phase 3"
        title="Lead Intake"
        description="Submit a new inbound lead, enrich it deterministically, score it, and write safe fields to the internal CRM-style record."
        badge={<StatusBadge status="ready" />}
      />

      {error ? <div className="notice errorNotice">{error}</div> : null}
      {loadError ? (
        <section className="card detailPanel">
          <p className="cardLabel">Lead result unavailable</p>
          <p>{loadError}</p>
        </section>
      ) : null}

      <section className="leadIntakeLayout">
        <LeadIntakeForm />
        <LeadResultPanel record={record} />
      </section>
    </div>
  );
}

function LeadIntakeForm() {
  return (
    <section className="card leadIntakePanel">
      <div>
        <p className="cardLabel">New inbound lead</p>
        <h2 className="sectionTitle">Intake form</h2>
      </div>

      <form action={submitLeadIntakeAction} className="leadIntakeForm">
        <div className="formGrid">
          <Field name="first_name" label="First name" defaultValue="Maya" />
          <Field name="last_name" label="Last name" defaultValue="Chen" />
          <Field name="email" label="Email" defaultValue="maya.chen@northstaranalytics.example" required />
          <Field name="company" label="Company" defaultValue="Northstar Analytics" required />
          <Field name="job_title" label="Job title" defaultValue="VP of Sales" />
          <Field name="company_website" label="Company website" defaultValue="https://northstaranalytics.example" />
          <Field name="company_size" label="Company size" defaultValue="201-500" />
          <Field name="industry" label="Industry" defaultValue="Analytics" />
          <Field name="region" label="Region" defaultValue="North America" />
          <Field name="source" label="Source" defaultValue="demo_request" required />
          <Field name="urgency" label="Urgency" defaultValue="this_week" />
          <Field name="budget_context" label="Budget context" defaultValue="Approved budget" />
          <Field name="crm_system" label="CRM system" defaultValue="HubSpot" />
        </div>

        <label className="textAreaField">
          <span>Message</span>
          <textarea
            name="message"
            defaultValue="We want a demo this week. Our reps are spending too much time qualifying inbound leads and we need better routing before the next campaign launch."
            rows={5}
          />
        </label>

        <label className="textAreaField">
          <span>Pain points</span>
          <textarea
            name="pain_points"
            defaultValue="Lead routing, inbound volume, manual qualification"
            rows={3}
          />
        </label>

        <label className="textAreaField">
          <span>Notes</span>
          <textarea name="notes" rows={3} />
        </label>

        <label className="checkboxField">
          <input name="requested_demo" type="checkbox" defaultChecked />
          <span>Requested demo</span>
        </label>

        <div className="actionRow">
          <button className="primaryButton" type="submit">
            Submit lead
          </button>
          <button className="secondaryButton" name="preset" type="submit" value="clean">
            Clean mid-market lead
          </button>
          <button className="secondaryButton" name="preset" type="submit" value="high_priority">
            High-priority lead
          </button>
          <button className="secondaryButton" name="preset" type="submit" value="risky">
            Risky/ambiguous lead
          </button>
        </div>
      </form>
    </section>
  );
}

function LeadResultPanel({ record }: { record: CRMLeadRecord | null }) {
  if (!record) {
    return (
      <section className="card leadIntakePanel">
        <p className="cardLabel">Result</p>
        <p className="emptyResultText">
          Submit a lead or use a demo preset to see enrichment, scoring, routing,
          CRM update status, and review visibility.
        </p>
      </section>
    );
  }

  return (
    <section className="card leadIntakePanel">
      <div className="reviewItemHeader">
        <div>
          <p className="cardLabel">Result</p>
          <h2 className="sectionTitle">{record.company}</h2>
          <p className="reviewMeta">
            {record.contact_name || "Unknown contact"} | {record.email}
          </p>
        </div>
        <div className="badgeRow">
          <span className={`miniBadge ${crmStatusTone(record.crm_update_status)}`}>
            {formatLabel(record.crm_update_status)}
          </span>
          {record.human_review_required ? (
            <span className="miniBadge badge-review">review created</span>
          ) : (
            <span className="miniBadge step-success">auto applied</span>
          )}
        </div>
      </div>

      <dl className="reviewDetails leadResultDetails">
        <Detail label="Lead score" value={String(record.lead_score)} />
        <Detail label="Priority" value={record.priority} />
        <Detail label="Confidence" value={record.confidence} />
        <Detail label="Urgency" value={record.urgency} />
        <Detail label="Persona" value={formatLabel(record.enriched_persona)} />
        <Detail label="Company size" value={formatLabel(record.company_size_band)} />
      </dl>

      <div className="reviewBlock">
        <p className="cardLabel">CRM update status</p>
        <p>{formatLabel(record.crm_update_status)}</p>
      </div>

      <div className="reviewBlock">
        <p className="cardLabel">Review created</p>
        <p>{record.human_review_required ? "Yes" : "No"}</p>
      </div>

      <div className="reviewBlock">
        <p className="cardLabel">Enrichment summary</p>
        <p>
          {formatLabel(record.industry_normalized)} company in{" "}
          {formatLabel(record.region_normalized)}. CRM-style record{" "}
          {formatLabel(record.crm_update_status)}.
        </p>
      </div>

      <div className="reviewBlock">
        <p className="cardLabel">Recommended route</p>
        <p>{record.recommended_route}</p>
      </div>

      <div className="reviewBlock">
        <p className="cardLabel">Next best action</p>
        <p>{record.next_best_action}</p>
      </div>

      {record.risk_flags.length > 0 ? (
        <div className="reviewBlock">
          <p className="cardLabel">Risk flags</p>
          <ul className="compactList">
            {record.risk_flags.map((flag) => (
              <li key={flag}>{formatLabel(flag)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="adminLinkRow">
        <a href={`/crm-records?record=${encodeURIComponent(record.crm_record_id)}`}>
          View CRM Record
        </a>
        <a href="/crm-records">CRM Records</a>
        <a href="/review-queue">Review Queue</a>
        <a href="/audit-trail">Audit Trail</a>
        <a href="/operational-logs">Operational Logs</a>
      </div>
    </section>
  );
}

function Field({
  name,
  label,
  defaultValue,
  required = false,
}: {
  name: string;
  label: string;
  defaultValue?: string;
  required?: boolean;
}) {
  return (
    <label className="textField">
      <span>{label}</span>
      <input name={name} defaultValue={defaultValue} required={required} />
    </label>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

async function submitLeadIntakeAction(formData: FormData) {
  "use server";

  const preset = String(formData.get("preset") || "");
  const request = preset ? presetRequest(preset) : requestFromForm(formData);
  let target = "/lead-intake";

  try {
    const result = await submitLeadIntake(request);
    target = `/lead-intake?lead_id=${encodeURIComponent(result.lead_id)}`;
  } catch (error) {
    target = `/lead-intake?error=${encodeURIComponent(errorMessage(error))}`;
  }

  redirect(target);
}

async function loadLeadRecord(leadId: string) {
  try {
    return { record: await getLeadIntakeRecord(leadId), loadError: "" };
  } catch (error) {
    return {
      record: null,
      loadError:
        error instanceof Error ? error.message : "The lead record could not be loaded.",
    };
  }
}

function requestFromForm(formData: FormData): LeadIntakeRequest {
  return {
    first_name: textValue(formData, "first_name"),
    last_name: textValue(formData, "last_name"),
    email: textValue(formData, "email"),
    company: textValue(formData, "company"),
    job_title: textValue(formData, "job_title"),
    company_website: textValue(formData, "company_website"),
    company_size: textValue(formData, "company_size"),
    industry: textValue(formData, "industry"),
    region: textValue(formData, "region"),
    source: textValue(formData, "source"),
    message: textValue(formData, "message"),
    pain_points: splitList(textValue(formData, "pain_points")),
    urgency: textValue(formData, "urgency"),
    budget_context: textValue(formData, "budget_context"),
    requested_demo: formData.get("requested_demo") === "on",
    crm_system: textValue(formData, "crm_system"),
    notes: textValue(formData, "notes"),
  };
}

function presetRequest(preset: string): LeadIntakeRequest {
  if (preset === "risky") {
    return {
      first_name: "Test",
      last_name: "User",
      email: "student.test@example.com",
      company: "Unknown Co",
      job_title: "Student",
      company_size: "unknown",
      industry: "",
      region: "",
      source: "contact_form",
      message: "This is for a school assignment, please ignore.",
      pain_points: ["unclear need"],
      urgency: "unknown",
      budget_context: "unknown",
      requested_demo: false,
      crm_system: "unknown",
      notes: "Risky demo preset.",
    };
  }

  if (preset === "high_priority") {
    return {
      first_name: "Maya",
      last_name: "Chen",
      email: "maya.chen@northstaranalytics.example",
      company: "Northstar Analytics",
      job_title: "VP of Sales",
      company_website: "https://northstaranalytics.example",
      company_size: "201-500",
      industry: "Analytics",
      region: "North America",
      source: "demo_request",
      message:
        "We want a demo this week. Our reps are spending too much time qualifying inbound leads and we need better routing before the next campaign launch.",
      pain_points: ["Lead routing", "Inbound volume", "Manual qualification"],
      urgency: "this_week",
      budget_context: "Approved budget",
      requested_demo: true,
      crm_system: "HubSpot",
      notes: "High-priority demo preset.",
    };
  }

  return {
    first_name: "Nadia",
    last_name: "Patel",
    email: "nadia.patel@localgrowth.example",
    company: "Local Growth Studio",
    job_title: "Operations Manager",
    company_website: "https://localgrowth.example",
    company_size: "51-200",
    industry: "Marketing Services",
    region: "EMEA",
    source: "webinar",
    message:
      "We are evaluating CRM cleanup for our sales team. Timing is flexible, and we are gathering options.",
    pain_points: ["CRM cleanup"],
    urgency: "60_days",
    budget_context: "Planned budget",
    requested_demo: false,
    crm_system: "HubSpot",
    notes: "Clean mid-market demo preset.",
  };
}

function textValue(formData: FormData, key: string) {
  return String(formData.get(key) || "").trim();
}

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function textParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Lead intake failed.";
}

function crmStatusTone(status: CRMLeadRecord["crm_update_status"]) {
  if (status === "blocked_pending_review") {
    return "event-danger";
  }
  if (status === "applied_with_review_visibility") {
    return "event-warning";
  }
  return "event-success";
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}
