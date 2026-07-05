import { DetailCard } from "@/components/DetailCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function LeadScoringPage() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Workflow 1"
        title="Lead Scoring"
        description="Explainable lead priority, routing suggestions, confidence, and review visibility for inbound sales work."
        badge={<StatusBadge status="ready" />}
      />
      <section className="twoColumn">
        <DetailCard label="Current behavior" title="Deterministic scoring">
          <p>
            The backend scores leads using transparent rules for intent, urgency,
            role, budget, CRM context, and suspicious signals.
          </p>
          <p>
            High-value leads can move quickly while risky or low-confidence leads
            remain visible for review.
          </p>
        </DetailCard>
        <DetailCard label="Guardrail" title="No hidden automation">
          <p>
            Scoring can recommend a route, but sensitive CRM ownership or stage
            changes stay governed by audit, observability, and review policy.
          </p>
        </DetailCard>
      </section>
    </div>
  );
}
