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
            The suite does not add authentication, n8n, LangGraph, or LLM calls
            yet. HubSpot remains sandbox/env controlled, and every workflow must
            keep audit trail plus operational observability.
          </p>
        </div>
      </section>
    </div>
  );
}
