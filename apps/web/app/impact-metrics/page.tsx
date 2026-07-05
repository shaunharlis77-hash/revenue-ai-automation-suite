import { DetailCard } from "@/components/DetailCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function ImpactMetricsPage() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Operations"
        title="Impact Metrics"
        description="Measurement space for time saved, review throughput, workflow adoption, and revenue operations quality."
        badge={<StatusBadge status="draft" />}
      />
      <section className="twoColumn">
        <DetailCard label="Measurement model" title="Business impact">
          <p>
            Future metrics should compare automation-assisted work with baseline
            sales operations effort, response speed, review throughput, and data
            quality.
          </p>
        </DetailCard>
        <DetailCard label="Source of truth" title="Use persisted events">
          <p>
            Impact should come from workflow runs, audit events, review items,
            CRM records, and operational step events rather than hand-entered
            demo numbers.
          </p>
        </DetailCard>
      </section>
    </div>
  );
}
