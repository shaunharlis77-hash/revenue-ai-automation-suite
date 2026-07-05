import Link from "next/link";

import { DashboardTable } from "@/components/DashboardTable";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionHeader } from "@/components/SectionHeader";
import { StatusBadge } from "@/components/StatusBadge";
import {
  getAdminDashboardMetrics,
  type AdminDashboardMetrics,
} from "@/lib/api";

export default async function AdminDashboardPage() {
  const { data, error } = await loadMetrics();

  return (
    <div className="pageStack dashboardPage">
      <PageHeader
        eyebrow="Phase 6"
        title="Admin / Operations Dashboard"
        description="System health, governance, workflow reliability, review queue, and CRM sync diagnostics."
        badge={<StatusBadge status="ready" />}
      />

      {error ? <ErrorState message={error} /> : null}

      {data ? (
        <>
          <section>
            <SectionHeader
              title="System Status"
              description="Operational health at a glance across adapter mode, workflow runs, reviews, and failures."
            />
            <div className="metricGrid">
              <MetricCard
                label="Adapter mode"
                value={formatLabel(text(data.system_status.adapter_mode))}
                note="Current CRM adapter selected by configuration."
                tone="neutral"
              />
              <MetricCard
                label="HubSpot configured"
                value={yesNo(data.system_status.hubspot_configured)}
                note="Whether a token is configured, without exposing it."
                tone={data.system_status.hubspot_configured ? "good" : "warning"}
              />
              <MetricCard
                label="Workflow runs"
                value={metric(data.system_status.total_workflow_runs)}
                note="Persisted workflow runs."
              />
              <MetricCard
                label="Open reviews"
                value={metric(data.system_status.open_review_items)}
                note="Pending human-review items."
                tone="review"
              />
              <MetricCard
                label="Failed runs"
                value={metric(data.system_status.failed_workflow_runs)}
                note="Workflow runs marked failed."
                tone={data.system_status.failed_workflow_runs ? "danger" : "good"}
              />
              <MetricCard
                label="Partial syncs"
                value={metric(data.system_status.partial_workflow_runs)}
                note="External syncs that preserved core records with diagnostics."
                tone={data.system_status.partial_workflow_runs ? "warning" : "good"}
              />
              <MetricCard
                label="Recent sync"
                value={formatLabel(text(data.system_status.recent_sync_status))}
                note="Latest HubSpot sync status from CRM records."
              />
              <MetricCard
                label="Failures last 24h"
                value={metric(data.system_status.operational_failures_last_24h)}
                note="Step-level failures in the last day."
                tone={data.system_status.operational_failures_last_24h ? "danger" : "good"}
              />
            </div>
          </section>

          <section className="twoColumn">
            <div className="card detailPanel">
              <SectionHeader
                title="Review Queue Health"
                description="Pending decisions and review queue distribution."
              />
              <div className="dashboardMiniGrid">
                <InsightBlock label="Pending" value={metric(data.review_queue_health.pending)} />
                <InsightBlock label="Approved" value={metric(data.review_queue_health.approved)} />
                <InsightBlock label="Rejected" value={metric(data.review_queue_health.rejected)} />
                <InsightBlock
                  label="Oldest pending"
                  value={formatDate(text(data.review_queue_health.oldest_pending_review))}
                />
              </div>
            </div>

            <div className="card detailPanel">
              <SectionHeader
                title="HubSpot Sync Health"
                description="Sandbox sync health without exposing credentials."
              />
              <div className="dashboardMiniGrid">
                <InsightBlock label="Successful" value={metric(data.hubspot_sync_health.successful_syncs)} />
                <InsightBlock label="Partial" value={metric(data.hubspot_sync_health.partial_syncs)} />
                <InsightBlock label="Failed" value={metric(data.hubspot_sync_health.failed_syncs)} />
                <InsightBlock
                  label="Missing IDs"
                  value={metric(data.hubspot_sync_health.records_missing_hubspot_ids)}
                />
              </div>
            </div>
          </section>

          <section className="twoColumn">
            <div className="card detailPanel">
              <SectionHeader
                title="Operational Health"
                description="Step-level failures, warnings, retryability, and recommended fixes."
              />
              <div className="dashboardMiniGrid">
                <InsightBlock label="Step events" value={metric(data.operational_health.total_step_events)} />
                <InsightBlock label="Failed steps" value={metric(data.operational_health.failed_step_events)} />
                <InsightBlock label="Warnings" value={metric(data.operational_health.warning_step_events)} />
                <InsightBlock label="Retryable" value={metric(data.operational_health.retryable_failures)} />
              </div>
            </div>

            <div className="card detailPanel">
              <SectionHeader
                title="Audit Health"
                description="Governance traceability, guardrails, blocked actions, and human-review events."
              />
              <div className="dashboardMiniGrid">
                <InsightBlock label="Audit events" value={metric(data.audit_health.total_audit_events)} />
                <InsightBlock
                  label="Guardrails"
                  value={metric(arrayCount(data.audit_health.recent_guardrail_events))}
                />
                <InsightBlock
                  label="Blocked actions"
                  value={metric(arrayCount(data.audit_health.recent_blocked_actions))}
                />
                <InsightBlock
                  label="Review events"
                  value={metric(arrayCount(data.audit_health.recent_human_review_required_events))}
                />
              </div>
            </div>
          </section>

          <section className="card detailPanel">
            <SectionHeader
              title="Workflow Health"
              description="Run status by workflow, including latest failure reason when available."
            />
            <DashboardTable
              columns={["Workflow", "Runs", "Success", "Failed", "Partial", "Latest", "Failure reason"]}
              rows={data.workflow_health.map((item) => [
                formatLabel(text(item.workflow_name)),
                metric(item.total_runs),
                metric(item.success_count),
                metric(item.failure_count),
                metric(item.partial_count),
                formatLabel(text(item.latest_status)),
                text(item.latest_failure_reason) || "None",
              ])}
            />
          </section>

          <section className="card detailPanel">
            <SectionHeader
              title="Recent Failed Operational Steps"
              description="Technical failures with safe messages and recommended fixes."
            />
            <DashboardTable
              columns={["When", "Workflow", "Step", "Severity", "Retryable", "Recommended fix"]}
              rows={arrayItems(data.operational_health.recent_failed_steps)
                .slice(0, 10)
                .map((item) => [
                  formatDate(text(item.created_at)),
                  formatLabel(text(item.workflow_name)),
                  formatLabel(text(item.step_name)),
                  formatLabel(text(item.severity)),
                  item.retryable ? "Yes" : "No",
                  text(item.recommended_fix) || "Not available",
                ])}
            />
          </section>

          <section className="card detailPanel">
            <SectionHeader
              title="Recommended Fixes"
              description="Most common operational fixes from failed workflow step events."
            />
            <DashboardTable
              columns={["Recommended fix", "Count"]}
              rows={arrayItems(data.operational_health.recommended_fixes).map((item) => [
                text(item.recommended_fix),
                metric(item.count),
              ])}
            />
          </section>

          <section className="card detailPanel">
            <SectionHeader
              title="Quick Links"
              description="Jump to the operational surfaces used for review, traceability, and maintenance."
            />
            <div className="adminLinkRow">
              {data.action_links.map((link) => (
                <Link key={link.route} href={link.route}>
                  {link.label}
                </Link>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

async function loadMetrics() {
  try {
    return { data: await getAdminDashboardMetrics(), error: "" };
  } catch (error) {
    return {
      data: null as AdminDashboardMetrics | null,
      error:
        error instanceof Error
          ? error.message
          : "Admin dashboard metrics could not be loaded.",
    };
  }
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
  return "0";
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function yesNo(value: unknown): string {
  return value ? "Yes" : "No";
}

function formatLabel(value: string): string {
  return value ? value.replace(/[_-]/g, " ") : "Not available";
}

function formatDate(value: string): string {
  if (!value) {
    return "Not available";
  }
  return new Date(value).toLocaleString();
}

function arrayCount(value: unknown): number {
  return Array.isArray(value) ? value.length : 0;
}

function arrayItems(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [];
}
