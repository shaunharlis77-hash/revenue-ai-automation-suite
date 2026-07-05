import { DetailCard } from "@/components/DetailCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function ProposalDraftsPage() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Workflow 4"
        title="Proposal Drafts"
        description="Internal proposal and package outlines prepared for rep review, with pricing, legal, security, and implementation guardrails."
        badge={<StatusBadge status="ready" />}
      />
      <section className="twoColumn">
        <DetailCard label="Current behavior" title="Outline, not final proposal">
          <p>
            The workflow prepares executive summary, scope, assumptions,
            exclusions, risk notes, review reasons, confidence, and next action.
          </p>
        </DetailCard>
        <DetailCard label="Guardrail" title="Human approval required">
          <p>
            Every proposal outline requires review and avoids final quote,
            fixed-price, binding proposal, legal, security, or delivery promises.
          </p>
        </DetailCard>
      </section>
    </div>
  );
}
