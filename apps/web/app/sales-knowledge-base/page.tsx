import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function SalesKnowledgeBasePage() {
  return (
    <div className="pageStack">
      <PageHeader
        title="Sales Knowledge Base"
        description="Placeholder space for approved answers, sales process notes, objections, positioning, and enablement materials."
        badge={<StatusBadge status="ready" />}
      />
      <section className="card detailPanel">
        <p>
          Future AI workflows should draw from approved knowledge and clearly
          show what source material informed each suggestion.
        </p>
      </section>
    </div>
  );
}

