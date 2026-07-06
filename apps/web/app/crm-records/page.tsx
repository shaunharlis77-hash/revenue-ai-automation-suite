import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import {
  getCRMLeadRecordActivities,
  getCRMLeadRecords,
  type CRMActivity,
  type CRMLeadRecord,
} from "@/lib/api";

type CRMRecordsPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

type CRMRecordWithActivities = {
  record: CRMLeadRecord;
  activities: CRMActivity[];
};

export default async function CRMRecordsPage({
  searchParams,
}: CRMRecordsPageProps) {
  const params = searchParams ? await searchParams : {};
  const selectedRecordId = textParam(params.record);
  const { records, loadError } = await loadCRMRecords();
  const selectedRecord =
    records.find((item) => item.record.crm_record_id === selectedRecordId) ||
    records[0] ||
    null;

  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Phase 5"
        title="CRM Records"
        description="CRM adapter records showing safe internal write-back, HubSpot sandbox sync status, review visibility, and related CRM activities."
        badge={<StatusBadge status="ready" />}
      />

      {loadError ? (
        <ErrorState
          message="CRM records could not be loaded. Start the backend and refresh this page."
          detail={loadError}
        />
      ) : null}

      {!loadError && records.length === 0 ? (
        <EmptyState
          title="No CRM records"
          message="Submit a lead from Lead Intake or run the demo journey to populate internal CRM-style records, sync status, review visibility, and activity history."
        />
      ) : null}

      {!loadError && records.length > 0 ? (
        <section className="crmRecordsLayout">
          <div className="crmRecordList">
            {records.map(({ record }) => (
              <CRMRecordCard
                key={record.crm_record_id}
                record={record}
                selected={record.crm_record_id === selectedRecord?.record.crm_record_id}
              />
            ))}
          </div>

          {selectedRecord ? (
            <CRMRecordDetail
              record={selectedRecord.record}
              activities={selectedRecord.activities}
            />
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

async function loadCRMRecords() {
  try {
    const rawRecords = await getCRMLeadRecords();
    const records = await Promise.all(
      rawRecords.map(async (record) => ({
        record,
        activities: await getCRMLeadRecordActivities(record.crm_record_id),
      })),
    );
    return { records, loadError: "" };
  } catch (error) {
    return {
      records: [] as CRMRecordWithActivities[],
      loadError:
        error instanceof Error
          ? error.message
          : "CRM records could not be loaded.",
    };
  }
}

function CRMRecordCard({
  record,
  selected,
}: {
  record: CRMLeadRecord;
  selected: boolean;
}) {
  return (
    <a
      className={`card crmRecordCard ${selected ? "selectedRecord" : ""}`}
      href={`/crm-records?record=${encodeURIComponent(record.crm_record_id)}`}
    >
      <div className="reviewItemHeader">
        <div>
          <h2 className="reviewTitle">{record.company}</h2>
          <p className="reviewMeta">
            {record.contact_name || "Unknown contact"} / {record.email}
          </p>
        </div>
        <div className="badgeRow">
          <StatusMiniBadge value={record.crm_update_status} />
          <HubSpotSyncBadge record={record} />
          <PriorityBadge value={record.priority} />
        </div>
      </div>
      <dl className="reviewDetails crmRecordSummary">
        <Detail label="Score" value={String(record.lead_score)} />
        <Detail label="Confidence" value={record.confidence} />
        <Detail label="Persona" value={formatLabel(record.enriched_persona)} />
        <Detail label="Updated" value={formatDate(record.updated_at)} />
      </dl>
      <p className="reviewMeta">{record.recommended_route}</p>
    </a>
  );
}

function CRMRecordDetail({
  record,
  activities,
}: {
  record: CRMLeadRecord;
  activities: CRMActivity[];
}) {
  const workflowRunId = textMeta(record.metadata_json.workflow_run_id);

  return (
    <section className="card crmRecordDetail">
      <div className="reviewItemHeader">
        <div>
          <p className="cardLabel">Selected CRM record</p>
          <h2 className="sectionTitle">{record.company}</h2>
          <p className="reviewMeta">
            {record.contact_name || "Unknown contact"} / {record.email}
          </p>
        </div>
        <div className="badgeRow">
          <StatusMiniBadge value={record.crm_update_status} />
          <span className="miniBadge badge-crm">{adapterDisplayLabel(record)}</span>
          <HubSpotSyncBadge record={record} />
          {record.human_review_required ? (
            <span className="miniBadge badge-review">review required</span>
          ) : (
            <span className="miniBadge step-success">safe auto update</span>
          )}
        </div>
      </div>

      <dl className="reviewDetails crmRecordDetails">
        <Detail label="CRM record id" value={record.crm_record_id} />
        <Detail label="Lead id" value={record.lead_id} />
        <Detail label="Source" value={formatLabel(record.source)} />
        <Detail label="Lead score" value={String(record.lead_score)} />
        <Detail label="Priority" value={record.priority} />
        <Detail label="Confidence" value={record.confidence} />
        <Detail label="Urgency" value={record.urgency} />
        <Detail label="Persona" value={formatLabel(record.enriched_persona)} />
        <Detail label="Company size" value={formatLabel(record.company_size_band)} />
        <Detail label="Industry" value={formatLabel(record.industry_normalized)} />
        <Detail label="Region" value={formatLabel(record.region_normalized)} />
        <Detail label="Updated" value={formatDate(record.updated_at)} />
      </dl>

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

      <div className="reviewBlock">
        <p className="cardLabel">HubSpot sync</p>
        <dl className="reviewDetails crmRecordSummary">
          <Detail label="Adapter" value={adapterDisplayLabel(record)} />
          <Detail label="Sync status" value={hubspotSyncDisplayLabel(record)} />
          <Detail label="Contact ID" value={record.hubspot_contact_id || "Not set"} />
          <Detail label="Company ID" value={record.hubspot_company_id || "Not set"} />
          <Detail label="Deal ID" value={record.hubspot_deal_id || "Not set"} />
          <Detail label="Last sync" value={record.last_hubspot_sync_at ? formatDate(record.last_hubspot_sync_at) : "Not synced"} />
        </dl>
        {record.hubspot_sync_error ? (
          <p className="errorText">{record.hubspot_sync_error}</p>
        ) : null}
      </div>

      <div className="reviewBlock">
        <p className="cardLabel">CRM activities</p>
        {activities.length === 0 ? (
          <p>No CRM activities are recorded for this mock CRM record yet.</p>
        ) : (
          <div className="crmActivityList">
            {activities.map((activity) => (
              <article className="crmActivity" key={activity.crm_activity_id}>
                <div>
                  <h3>{activity.activity_title}</h3>
                  <p>{activity.activity_body}</p>
                  <p className="reviewMeta">
                    {formatLabel(activity.activity_type)} / {formatDate(activity.created_at)}
                  </p>
                </div>
                <span className={`miniBadge ${activityTone(activity.activity_status)}`}>
                  {formatLabel(activity.activity_status)}
                </span>
              </article>
            ))}
          </div>
        )}
      </div>

      <div className="adminLinkRow">
        <a href="/lead-intake">Lead Intake</a>
        <a href="/hubspot-status">HubSpot Status</a>
        <a href="/review-queue">Review Queue</a>
        <a href="/audit-trail">Audit Trail</a>
        <a href="/operational-logs">Operational Logs</a>
        {workflowRunId ? (
          <a href={`/operational-logs?filter=${encodeURIComponent(workflowRunId)}`}>
            This workflow run
          </a>
        ) : null}
      </div>
    </section>
  );
}

function StatusMiniBadge({
  value,
}: {
  value: CRMLeadRecord["crm_update_status"];
}) {
  return <span className={`miniBadge ${crmStatusTone(value)}`}>{formatLabel(value)}</span>;
}

function PriorityBadge({ value }: { value: string }) {
  const tone = value === "critical" || value === "high" ? "event-warning" : "badge-crm";
  return <span className={`miniBadge ${tone}`}>{formatLabel(value)}</span>;
}

function HubSpotSyncBadge({ record }: { record: CRMLeadRecord }) {
  return (
    <span className={`miniBadge ${hubspotSyncTone(record)}`}>
      {hubspotSyncDisplayLabel(record)}
    </span>
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

function crmStatusTone(status: CRMLeadRecord["crm_update_status"]) {
  if (status === "blocked_pending_review") {
    return "event-danger";
  }
  if (status === "applied_with_review_visibility") {
    return "event-warning";
  }
  return "event-success";
}

function activityTone(status: CRMActivity["activity_status"]) {
  if (status === "blocked") {
    return "event-danger";
  }
  if (status === "applied") {
    return "event-success";
  }
  return "badge-crm";
}

function hubspotSyncTone(record: CRMLeadRecord) {
  const status = record.hubspot_sync_status;
  if (isLocalCRMRecord(record)) {
    return "badge-crm";
  }
  if (status === "failed" || status === "blocked_pending_review") {
    return "event-danger";
  }
  if (status === "synced" && hasHubSpotObjectIds(record)) {
    return "event-success";
  }
  if (status === "partial_sync") {
    return "event-warning";
  }
  return "badge-crm";
}

function hubspotSyncDisplayLabel(record: CRMLeadRecord) {
  const status = record.hubspot_sync_status;

  if (isLocalCRMRecord(record)) {
    return "Local CRM Record";
  }
  if (status === "synced" && hasHubSpotObjectIds(record)) {
    return "Synced";
  }
  if (status === "synced") {
    return "Sync Pending Verification";
  }
  if (status === "partial_sync") {
    return "Partial Sync";
  }
  if (status === "failed") {
    return "Sync Failed";
  }
  if (status === "blocked_pending_review") {
    return "Blocked Pending Review";
  }
  if (status === "not_enabled") {
    return "Local CRM Record";
  }

  return formatLabel(status);
}

function adapterDisplayLabel(record: CRMLeadRecord) {
  return isLocalCRMRecord(record) ? "Local CRM Adapter" : "HubSpot Adapter";
}

function isLocalCRMRecord(record: CRMLeadRecord) {
  const status = record.hubspot_sync_status.toLowerCase();
  return (
    record.adapter_mode === "mock" ||
    status === "skipped_mock_mode" ||
    status.includes("mock mode skipped") ||
    status.includes("skipped because mock mode")
  );
}

function hasHubSpotObjectIds(record: CRMLeadRecord) {
  return Boolean(
    record.hubspot_contact_id || record.hubspot_company_id || record.hubspot_deal_id,
  );
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function textParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function textMeta(value: unknown) {
  return typeof value === "string" ? value : "";
}
