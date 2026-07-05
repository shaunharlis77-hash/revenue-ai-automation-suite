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
        description="A foundation dashboard for future sales AI automation. Everything shown here is placeholder data and no live systems are connected."
        badge={<StatusBadge status="planned" />}
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
            This dashboard does not authenticate users, call the API, connect to
            HubSpot, run n8n workflows, or generate AI content yet.
          </p>
        </div>
      </section>
    </div>
  );
}
