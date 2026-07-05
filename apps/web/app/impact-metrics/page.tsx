import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function ImpactMetricsPage() {
  return (
    <div className="pageStack">
      <PageHeader
        title="Impact Metrics"
        description="Placeholder space for measuring time saved, review throughput, workflow adoption, and revenue operations quality."
        badge={<StatusBadge status="planned" />}
      />
      <section className="card detailPanel">
        <p>
          Future metrics should compare automation-assisted work with baseline
          sales operations effort and quality.
        </p>
      </section>
    </div>
  );
}

