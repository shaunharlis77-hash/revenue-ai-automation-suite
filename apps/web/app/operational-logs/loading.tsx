import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function OperationalLogsLoading() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Admin"
        title="Operational Logs"
        description="Step-level workflow observability for failures, retries, and maintenance."
        badge={<StatusBadge status="ready" />}
      />
      <section className="card detailPanel">
        <p className="cardLabel">Loading</p>
        <p>Loading workflow step events...</p>
      </section>
    </div>
  );
}
