import { DetailCard } from "@/components/DetailCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function SalesKnowledgeBasePage() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Knowledge"
        title="Sales Knowledge Base"
        description="Approved sales context for future AI suggestions, including objections, process notes, positioning, and enablement material."
        badge={<StatusBadge status="ready" />}
      />
      <section className="twoColumn">
        <DetailCard label="Approved context" title="Ground future suggestions">
          <p>
            Future AI workflows should draw from approved knowledge and clearly
            show what source material informed each suggestion.
          </p>
        </DetailCard>
        <DetailCard label="Governance" title="No free-form source drift">
          <p>
            Sales answers, proposal language, and objection handling should stay
            tied to reviewed knowledge, SOPs, and audit-visible workflow output.
          </p>
        </DetailCard>
      </section>
    </div>
  );
}
