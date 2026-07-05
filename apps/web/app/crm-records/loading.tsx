import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";


export default function CRMRecordsLoading() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Phase 4"
        title="CRM Records"
        description="Loading mock CRM adapter records and activity history."
        badge={<StatusBadge status="draft" />}
      />
      <section className="card detailPanel">
        <p className="cardLabel">Loading</p>
        <p>Fetching CRM records from the local backend.</p>
      </section>
    </div>
  );
}
