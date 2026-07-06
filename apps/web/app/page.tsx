import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { WorkflowCard } from "@/components/WorkflowCard";
import { overviewMetrics, queueItems, workflowCards } from "@/lib/placeholders";

export default function OverviewPage() {
  return (
    <div className="pageStack">
      <PageHeader
        title="Overview"
        description="A suite overview for the Revenue AI automation foundation, including workflows, governance, CRM adapter boundaries, and operational guardrails."
        badge={<StatusBadge status="live" />}
      />

      <section className="metricGrid" aria-label="Foundation metrics">
        {overviewMetrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </section>

      <section className="workflowGrid" aria-label="Planned workflows">
        {workflowCards.map((workflow) => (
          <WorkflowCard
            key={workflow.title}
            title={workflow.title}
            status={workflow.status}
            description={workflow.description}
          />
        ))}
      </section>

      <section className="twoColumn">
        <div className="card detailPanel">
          <p className="cardLabel">Human Review Queue</p>
          {queueItems.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </div>
        <div className="card detailPanel">
          <p className="cardLabel">Current Boundary</p>
          <p>
            This demo runs as a local AI operating layer with HubSpot sandbox
            integration and n8n orchestration. Authentication, role-based access
            control, production deployment, queue-based retries, and Postgres
            persistence would be the next production hardening steps. Every
            workflow must keep audit trail coverage, operational observability,
            and human review for risky or customer-facing actions.
          </p>
        </div>
      </section>
    </div>
  );
}
