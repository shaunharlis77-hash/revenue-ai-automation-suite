import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function LeadScoringPage() {
  return (
    <div className="pageStack">
      <PageHeader
        title="Lead Scoring"
        description="Placeholder space for future lead prioritization rules, explainable scoring signals, and review workflows."
        badge={<StatusBadge status="planned" />}
      />
      <section className="card detailPanel">
        <p>
          Future versions may combine CRM fields, engagement signals, and sales
          context. This page currently uses no live data.
        </p>
      </section>
    </div>
  );
}

