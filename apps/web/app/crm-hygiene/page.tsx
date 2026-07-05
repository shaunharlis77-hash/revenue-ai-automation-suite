import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function CrmHygienePage() {
  return (
    <div className="pageStack">
      <PageHeader
        title="CRM Hygiene"
        description="Placeholder space for future CRM data quality checks, stale field detection, and duplicate review."
        badge={<StatusBadge status="planned" />}
      />
      <section className="card detailPanel">
        <p>
          Future CRM write-back should be gated by review and audit trails,
          especially when changing lifecycle or ownership fields.
        </p>
      </section>
    </div>
  );
}

