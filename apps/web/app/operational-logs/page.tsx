import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import {
  getWorkflowStepEvents,
  type WorkflowStepEvent,
} from "@/lib/api";

type OperationalLogsPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function OperationalLogsPage({
  searchParams,
}: OperationalLogsPageProps) {
  const params = searchParams ? await searchParams : {};
  const filter = textParam(params.filter)?.trim() || "";
  const { events, loadError } = await loadWorkflowStepEvents();
  const visibleEvents = filterEvents(events, filter);
  const failedEvents = visibleEvents.filter(
    (event) => event.step_status === "failed",
  );
  const summary = buildSummary(events);

  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Admin"
        title="Operational Logs"
        description="Step-level workflow observability for failures, retries, and maintenance."
        badge={<StatusBadge status="ready" />}
      />

      {loadError ? (
        <section className="card detailPanel">
          <p className="cardLabel">Backend unavailable</p>
          <p>{loadError}</p>
        </section>
      ) : null}

      {!loadError ? (
        <section className="metricGrid operationalMetricGrid">
          <MetricCard
            label="Total step events"
            value={String(summary.total)}
            note="All persisted workflow step events."
          />
          <MetricCard
            label="Failed steps"
            value={String(summary.failed)}
            note="Steps that need diagnosis."
          />
          <MetricCard
            label="Warning/skipped steps"
            value={String(summary.warningOrSkipped)}
            note="Warnings and intentional skips."
          />
          <MetricCard
            label="Critical/Error severity steps"
            value={String(summary.errorOrCritical)}
            note="Error or critical severity steps."
          />
          <MetricCard
            label="Retryable failures"
            value={String(summary.retryableFailures)}
            note="Failures marked safe to retry."
          />
          <MetricCard
            label="Unique workflow runs"
            value={String(summary.uniqueRuns)}
            note="Distinct workflow run ids represented."
          />
        </section>
      ) : null}

      {!loadError && events.length > 0 ? (
        <section className="card filterPanel">
          <form className="filterForm" action="/operational-logs">
            <label htmlFor="operational-filter">Filter logs</label>
            <input
              id="operational-filter"
              name="filter"
              placeholder="Workflow name or workflow run id"
              defaultValue={filter}
            />
            <button className="secondaryButton" type="submit">
              Apply
            </button>
            {filter ? (
              <a className="clearFilterLink" href="/operational-logs">
                Clear
              </a>
            ) : null}
          </form>
        </section>
      ) : null}

      {!loadError && events.length === 0 ? (
        <section className="card detailPanel">
          <p className="cardLabel">No workflow step events</p>
          <p>
            No operational step events have been recorded yet. Run the demo seed
            journey or execute a workflow to populate this page.
          </p>
        </section>
      ) : null}

      {!loadError && events.length > 0 && visibleEvents.length === 0 ? (
        <section className="card detailPanel">
          <p className="cardLabel">No matching step events</p>
          <p>No workflow step events match the current filter.</p>
        </section>
      ) : null}

      {!loadError && visibleEvents.length > 0 ? (
        <>
          <section className="sectionStack" aria-label="Failure diagnostics">
            <div>
              <p className="cardLabel">Failure diagnostics</p>
              <h2 className="sectionTitle">What failed and what to check</h2>
            </div>

            {failedEvents.length === 0 ? (
              <article className="card detailPanel">
                <p className="cardLabel">No failed steps</p>
                <p>
                  No failed workflow steps match the current view. Successful
                  and skipped steps are still listed below.
                </p>
              </article>
            ) : (
              <div className="operationalFailureList">
                {failedEvents.map((event) => (
                  <FailureDiagnosticCard
                    key={event.step_event_id}
                    event={event}
                  />
                ))}
              </div>
            )}
          </section>

          <section className="sectionStack" aria-label="Workflow step events">
            <div>
              <p className="cardLabel">Step events</p>
              <h2 className="sectionTitle">All workflow steps</h2>
            </div>
            <div className="operationalList">
              {visibleEvents.map((event) => (
                <StepEventCard key={event.step_event_id} event={event} />
              ))}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

async function loadWorkflowStepEvents() {
  try {
    return { events: await getWorkflowStepEvents(), loadError: "" };
  } catch (error) {
    return {
      events: [] as WorkflowStepEvent[],
      loadError:
        error instanceof Error
          ? error.message
          : "The operational logs could not be loaded.",
    };
  }
}

function FailureDiagnosticCard({ event }: { event: WorkflowStepEvent }) {
  return (
    <article className="operationalFailure">
      <div className="reviewItemHeader">
        <div>
          <h2 className="reviewTitle">{formatLabel(event.step_name)}</h2>
          <p className="reviewMeta">
            {formatLabel(event.workflow_name)} | {formatDate(event.created_at)}
          </p>
        </div>
        <div className="badgeRow">
          <StepStatusBadge value={event.step_status} />
          <SeverityBadge value={event.severity} />
          {event.retryable ? <span className="miniBadge badge-retry">retryable</span> : null}
        </div>
      </div>

      <dl className="reviewDetails operationalDetails">
        <Detail label="Workflow run" value={event.workflow_run_id} />
        <Detail label="Entity" value={`${event.entity_type || "unknown"} | ${event.entity_id || "unknown"}`} />
        <Detail label="Error type" value={event.error_type || "Not provided"} />
        <Detail label="Retryable" value={event.retryable ? "Yes" : "No"} />
      </dl>

      <div className="diagnosticGrid">
        <DiagnosticBlock label="Error message" value={event.error_message} />
        <DiagnosticBlock label="Failure reason" value={event.failure_reason} />
        <DiagnosticBlock label="Recommended fix" value={event.recommended_fix} />
      </div>
    </article>
  );
}

function StepEventCard({ event }: { event: WorkflowStepEvent }) {
  return (
    <article className="stepEvent">
      <div className="stepEventMain">
        <div>
          <p className="reviewMeta">{formatDate(event.created_at)}</p>
          <h2 className="reviewTitle">{formatLabel(event.step_name)}</h2>
          <p className="reviewMeta">
            {formatLabel(event.workflow_name)} | {event.workflow_run_id}
          </p>
        </div>
        <div className="badgeRow">
          <StepStatusBadge value={event.step_status} />
          <SeverityBadge value={event.severity} />
          {event.retryable ? <span className="miniBadge badge-retry">retryable</span> : null}
        </div>
      </div>

      <dl className="reviewDetails stepDetails">
        <Detail label="Entity type" value={event.entity_type || "None"} />
        <Detail label="Entity id" value={event.entity_id || "None"} />
        <Detail label="Status" value={event.step_status} />
        <Detail label="Severity" value={event.severity} />
        <Detail label="Retryable" value={event.retryable ? "Yes" : "No"} />
      </dl>
    </article>
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

function DiagnosticBlock({
  label,
  value,
}: {
  label: string;
  value?: string | null;
}) {
  return (
    <div className="diagnosticBlock">
      <p className="cardLabel">{label}</p>
      <p>{value || "Not provided"}</p>
    </div>
  );
}

function StepStatusBadge({
  value,
}: {
  value: WorkflowStepEvent["step_status"];
}) {
  return <span className={`miniBadge step-${value}`}>{value}</span>;
}

function SeverityBadge({ value }: { value: WorkflowStepEvent["severity"] }) {
  return <span className={`miniBadge severity-${value}`}>{value}</span>;
}

function buildSummary(events: WorkflowStepEvent[]) {
  const failed = events.filter((event) => event.step_status === "failed");
  return {
    total: events.length,
    failed: failed.length,
    warningOrSkipped: events.filter(
      (event) => event.step_status === "skipped" || event.severity === "warning",
    ).length,
    errorOrCritical: events.filter(
      (event) => event.severity === "error" || event.severity === "critical",
    ).length,
    retryableFailures: failed.filter((event) => event.retryable).length,
    uniqueRuns: new Set(events.map((event) => event.workflow_run_id)).size,
  };
}

function filterEvents(events: WorkflowStepEvent[], filter: string) {
  if (!filter) {
    return events;
  }

  const normalized = filter.toLowerCase();
  return events.filter(
    (event) =>
      event.workflow_name.toLowerCase().includes(normalized) ||
      event.workflow_run_id.toLowerCase().includes(normalized),
  );
}

function textParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
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
