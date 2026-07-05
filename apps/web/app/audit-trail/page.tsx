import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { getAuditEvents, type AuditEvent } from "@/lib/api";

export default async function AuditTrailPage() {
  const { events, loadError } = await loadAuditEvents();

  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Admin"
        title="Audit Trail"
        description="Review durable workflow events, guardrail triggers, human decisions, and CRM update recommendations."
        badge={<StatusBadge status="ready" />}
      />

      {loadError ? (
        <section className="card detailPanel">
          <p className="cardLabel">Backend unavailable</p>
          <p>{loadError}</p>
        </section>
      ) : null}

      {!loadError && events.length === 0 ? (
        <section className="card detailPanel">
          <p className="cardLabel">No audit events</p>
          <p>No durable audit events have been recorded yet.</p>
        </section>
      ) : null}

      {!loadError && events.length > 0 ? (
        <section className="auditList" aria-label="Audit events">
          {events.map((event) => (
            <AuditEventCard key={event.event_id} event={event} />
          ))}
        </section>
      ) : null}
    </div>
  );
}

async function loadAuditEvents() {
  try {
    return { events: await getAuditEvents(), loadError: "" };
  } catch (error) {
    return {
      events: [] as AuditEvent[],
      loadError:
        error instanceof Error
          ? error.message
          : "The audit trail could not be loaded.",
    };
  }
}

function AuditEventCard({ event }: { event: AuditEvent }) {
  return (
    <article className={`auditEvent ${eventTone(event.event_type)}`}>
      <div className="reviewItemHeader">
        <div>
          <h2 className="reviewTitle">{formatLabel(event.event_type)}</h2>
          <p className="reviewMeta">
            {formatDate(event.created_at)} · {formatLabel(event.workflow_name)}
          </p>
        </div>
        <div className="badgeRow">
          <span className={`miniBadge ${eventTone(event.event_type)}`}>
            {formatLabel(event.event_type)}
          </span>
          {event.human_review_required ? (
            <span className="miniBadge badge-review">human review required</span>
          ) : null}
        </div>
      </div>

      <dl className="reviewDetails">
        <div>
          <dt>Entity</dt>
          <dd>
            {formatLabel(event.entity_type)} · {event.entity_id}
          </dd>
        </div>
        <div>
          <dt>Actor</dt>
          <dd>{event.actor}</dd>
        </div>
        <div>
          <dt>Decision</dt>
          <dd>{event.decision || "None"}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{event.event_source}</dd>
        </div>
      </dl>

      {event.guardrails_triggered.length > 0 ? (
        <div className="reviewBlock">
          <p className="cardLabel">Guardrails triggered</p>
          <ul className="compactList">
            {event.guardrails_triggered.map((guardrail) => (
              <li key={guardrail}>{formatLabel(guardrail)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {event.decision_reason ? (
        <div className="reviewBlock">
          <p className="cardLabel">Decision reason</p>
          <p>{event.decision_reason}</p>
        </div>
      ) : null}
    </article>
  );
}

function eventTone(eventType: string) {
  if (eventType === "workflow_failed") {
    return "event-danger";
  }
  if (
    eventType === "guardrail_triggered" ||
    eventType === "crm_update_blocked"
  ) {
    return "event-warning";
  }
  if (
    eventType === "review_created" ||
    eventType === "review_approved" ||
    eventType === "review_rejected"
  ) {
    return "event-review";
  }
  if (eventType === "crm_update_applied") {
    return "event-success";
  }
  return "event-neutral";
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
