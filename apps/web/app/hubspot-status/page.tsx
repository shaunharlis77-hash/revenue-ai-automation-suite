import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { getHubSpotStatus, type HubSpotStatus } from "@/lib/api";


export default async function HubSpotStatusPage() {
  const { status, loadError } = await loadStatus();

  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Phase 5"
        title="HubSpot Status"
        description="Configuration status for the optional HubSpot sandbox adapter. Tokens are never displayed."
        badge={<StatusBadge status="ready" />}
      />

      {loadError ? (
        <section className="card detailPanel">
          <p className="cardLabel">Backend unavailable</p>
          <p>{loadError}</p>
        </section>
      ) : null}

      {status ? (
        <section className="card crmRecordDetail">
          <div className="reviewItemHeader">
            <div>
              <p className="cardLabel">Adapter configuration</p>
              <h2 className="sectionTitle">{formatLabel(status.status)}</h2>
              <p className="reviewMeta">
                Mock mode remains the safe default. HubSpot mode only runs when
                enabled with a configured private app token.
              </p>
            </div>
            <div className="badgeRow">
              <span className="miniBadge badge-crm">{formatLabel(status.adapter_mode)} mode</span>
              <span className={`miniBadge ${status.hubspot_enabled ? "event-success" : "step-skipped"}`}>
                {status.hubspot_enabled ? "enabled" : "disabled"}
              </span>
              <span className={`miniBadge ${status.token_configured ? "event-success" : "event-warning"}`}>
                {status.token_configured ? "token configured" : "token missing"}
              </span>
            </div>
          </div>

          <dl className="reviewDetails crmRecordDetails">
            <Detail label="Portal ID" value={status.portal_id || "Not configured"} />
            <Detail label="Default pipeline" value={yesNo(status.default_pipeline_configured)} />
            <Detail label="Default deal stage" value={yesNo(status.default_deal_stage_configured)} />
            <Detail label="Owner ID" value={yesNo(status.owner_id_configured)} />
          </dl>

          <div className="reviewBlock">
            <p className="cardLabel">Safety behavior</p>
            <p>
              Clean safe updates can sync automatically. High-priority leads can
              sync with review visibility. Risky or ambiguous leads block
              sensitive sync pending review. Customer-facing messages are never
              sent from this integration.
            </p>
          </div>

          <div className="adminLinkRow">
            <a href="/crm-records">CRM Records</a>
            <a href="/audit-trail">Audit Trail</a>
            <a href="/operational-logs">Operational Logs</a>
          </div>
        </section>
      ) : null}
    </div>
  );
}

async function loadStatus() {
  try {
    return { status: await getHubSpotStatus(), loadError: "" };
  } catch (error) {
    return {
      status: null as HubSpotStatus | null,
      loadError:
        error instanceof Error ? error.message : "HubSpot status could not be loaded.",
    };
  }
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function yesNo(value: boolean) {
  return value ? "Configured" : "Not configured";
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}
