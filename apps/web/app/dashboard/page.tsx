import { DashboardTable } from "@/components/DashboardTable";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionHeader } from "@/components/SectionHeader";
import { StatusBadge } from "@/components/StatusBadge";
import {
  getSalesManagerDashboardMetrics,
  type DropOffZone,
  type SalesManagerDashboardMetrics,
} from "@/lib/api";

export default async function SalesManagerDashboardPage() {
  const { data, error } = await loadMetrics();

  return (
    <div className="pageStack dashboardPage">
      <PageHeader
        eyebrow="Phase 6"
        title="Sales Manager Dashboard"
        description="AI-assisted revenue operations, team activity, follow-up discipline, drop-off zones, and measurable sales execution outcomes."
        badge={<StatusBadge status="ready" />}
      />

      {error ? <ErrorState message={error} /> : null}

      {data ? (
        <>
          <section>
            <SectionHeader
              title="Sales Overview"
              description="A quick read on volume, follow-up work, review load, and estimated time saved."
            />
            <div className="metricGrid">
              <MetricCard
                label="Leads processed"
                value={metric(data.sales_overview.total_leads_processed)}
                note="Inbound leads with persisted CRM-style records."
                tone="good"
              />
              <MetricCard
                label="High-priority leads"
                value={metric(data.sales_overview.high_priority_leads)}
                note="Leads marked high or critical."
                tone="warning"
              />
              <MetricCard
                label="Safe CRM updates"
                value={metric(data.sales_overview.crm_updates_applied)}
                note="Safe applied updates, including review-visibility updates."
                tone="good"
              />
              <MetricCard
                label="Human reviews pending"
                value={metric(data.sales_overview.open_review_items_affecting_sales)}
                note="Open review items affecting sales execution."
                tone="review"
              />
              <MetricCard
                label="Follow-ups drafted"
                value={metric(data.sales_overview.follow_ups_drafted)}
                note="AI-assisted customer-facing drafts prepared for review."
              />
              <MetricCard
                label="Proposals prepared"
                value={metric(data.sales_overview.proposals_recommended)}
                note="Internal proposal/package outlines prepared."
              />
              <MetricCard
                label="Estimated time saved"
                value={`${metric(data.sales_overview.estimated_time_saved_hours)}h`}
                note={`${metric(data.sales_overview.estimated_time_saved_minutes)} estimated minutes saved.`}
                tone="good"
              />
              <MetricCard
                label="AI adoption rate"
                value={`${metric(data.team_activity_and_ai_adoption.adoption_rate_percent)}%`}
                note="Used workflow types divided by available workflow types."
              />
            </div>
          </section>

          <section className="twoColumn">
            <div className="card detailPanel">
              <SectionHeader
                title="Lead And Pipeline Health"
                description="Where current leads stand by priority, persona, route, and review status."
              />
              <div className="dashboardMiniGrid">
                <InsightBlock
                  label="Priority breakdown"
                  value={formatBreakdown(data.lead_and_pipeline_health.lead_priority_breakdown)}
                />
                <InsightBlock
                  label="Routes"
                  value={formatBreakdown(data.lead_and_pipeline_health.leads_by_route)}
                />
                <InsightBlock
                  label="Blocked CRM updates"
                  value={metric(data.lead_and_pipeline_health.records_blocked_pending_review)}
                />
                <InsightBlock
                  label="Missing next steps"
                  value={metric(data.lead_and_pipeline_health.missing_next_step_count)}
                />
              </div>
            </div>

            <div className="card detailPanel">
              <SectionHeader
                title="Team AI Adoption"
                description="Workflow usage across the persisted system. Rep-level reporting appears when owner attribution exists."
              />
              <div className="dashboardMiniGrid">
                <InsightBlock
                  label="AI workflows used"
                  value={`${data.team_activity_and_ai_adoption.ai_assisted_workflows_used} / ${data.team_activity_and_ai_adoption.available_ai_workflows.length}`}
                />
                <InsightBlock
                  label="Total AI actions"
                  value={metric(data.team_activity_and_ai_adoption.total_ai_assisted_actions)}
                />
                <InsightBlock
                  label="Most used"
                  value={formatLabel(data.team_activity_and_ai_adoption.most_used_ai_workflow)}
                />
                <InsightBlock
                  label="Rep adoption"
                  value={formatLabel(data.team_activity_and_ai_adoption.rep_adoption_status)}
                />
              </div>
              {data.team_activity_and_ai_adoption.rep_level_recommendation ? (
                <p className="dashboardHint">
                  {data.team_activity_and_ai_adoption.rep_level_recommendation}
                </p>
              ) : null}
            </div>
          </section>

          <section>
            <SectionHeader
              title="Drop-Off Zones"
              description="Sales process points where leads, reviews, CRM updates, or sync work need manager attention."
            />
            <div className="dropOffGrid">
              {data.drop_off_zone_stats.top_drop_off_zones.map((zone) => (
                <DropOffZoneCard key={zone.zone_name} zone={zone} />
              ))}
            </div>
          </section>

          <section className="twoColumn">
            <div className="card detailPanel">
              <SectionHeader
                title="AI Impact"
                description="Estimated time saved and how often automation, review, and blocking controls are used."
              />
              <div className="dashboardMiniGrid">
                <InsightBlock
                  label="Safe automations"
                  value={metric(data.ai_impact.safe_automation_count)}
                />
                <InsightBlock
                  label="Review required"
                  value={metric(data.ai_impact.human_review_required_count)}
                />
                <InsightBlock
                  label="Blocked actions"
                  value={metric(data.ai_impact.blocked_action_count)}
                />
                <InsightBlock
                  label="Approval rate"
                  value={`${metric(data.ai_impact.ai_approval_rate_percent)}%`}
                />
              </div>
              <p className="dashboardHint">
                Time saved is estimated from workflow type and safe automation counts, not tracked rep time.
              </p>
            </div>

            <div className="card detailPanel">
              <SectionHeader
                title="Sales Execution Risks"
                description="Business-facing risks that may slow down sales execution."
              />
              <DashboardTable
                columns={["Risk", "Count"]}
                rows={[
                  ["Pending reviews", metric(data.sales_execution_risks.pending_reviews)],
                  ["Blocked CRM updates", metric(data.sales_execution_risks.blocked_crm_updates)],
                  ["Missing next steps", metric(data.sales_execution_risks.missing_next_steps)],
                  [
                    "HubSpot sync needs attention",
                    metric(data.sales_execution_risks.failed_or_partial_hubspot_syncs_affecting_sales),
                  ],
                  [
                    "High-priority leads need attention",
                    metric(data.sales_execution_risks.high_priority_leads_needing_attention),
                  ],
                ]}
              />
            </div>
          </section>

          <section className="card detailPanel">
            <SectionHeader
              title="Recent Revenue Activity"
              description="Latest business-relevant workflow events, translated into sales-manager language."
            />
            <DashboardTable
              columns={["When", "Action", "Workflow", "Company", "Status", "Review"]}
              rows={data.recent_revenue_activity.slice(0, 12).map((item) => [
                formatDate(text(item.timestamp)),
                text(item.sales_manager_label) || text(item.business_action),
                formatLabel(text(item.workflow_name)),
                text(item.company) || "Not available",
                formatLabel(text(item.status)),
                item.human_review_required ? "Required" : "Not required",
              ])}
            />
          </section>
        </>
      ) : null}
    </div>
  );
}

async function loadMetrics() {
  try {
    return { data: await getSalesManagerDashboardMetrics(), error: "" };
  } catch (error) {
    return {
      data: null as SalesManagerDashboardMetrics | null,
      error:
        error instanceof Error
          ? error.message
          : "Sales manager dashboard metrics could not be loaded.",
    };
  }
}

function DropOffZoneCard({ zone }: { zone: DropOffZone }) {
  const count =
    zone.count === "not_enough_data" ? "Not enough data" : String(zone.count);
  return (
    <article className={`card dropOffCard risk-${zone.severity}`}>
      <div className="reviewItemHeader">
        <h3>{zone.zone_name}</h3>
        <span className={`miniBadge risk-${zone.severity}`}>{zone.severity}</span>
      </div>
      <p className="dropOffCount">{count}</p>
      <p>{zone.suggested_manager_action}</p>
    </article>
  );
}

function InsightBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="diagnosticBlock">
      <p className="cardLabel">{label}</p>
      <p>{value}</p>
    </div>
  );
}

function metric(value: unknown): string {
  if (typeof value === "number") {
    return String(value);
  }
  if (typeof value === "string") {
    return value;
  }
  if (isNotEnoughData(value)) {
    return "Not enough data";
  }
  return "0";
}

function formatBreakdown(value: unknown): string {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return "Not enough data";
  }
  const entries = Object.entries(value as Record<string, unknown>);
  if (entries.length === 0) {
    return "No records yet";
  }
  return entries
    .slice(0, 3)
    .map(([key, item]) => `${key}: ${String(item)}`)
    .join(", ");
}

function isNotEnoughData(value: unknown): value is { status: string; reason: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    (value as { status?: string }).status === "not_enough_data"
  );
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function formatLabel(value: unknown): string {
  const raw = typeof value === "string" && value ? value : "Not available";
  return raw.replace(/[_-]/g, " ");
}

function formatDate(value: string): string {
  if (!value) {
    return "Not available";
  }
  return new Date(value).toLocaleString();
}
