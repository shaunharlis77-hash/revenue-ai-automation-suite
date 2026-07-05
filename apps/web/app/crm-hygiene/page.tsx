import { DetailCard } from "@/components/DetailCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function CrmHygienePage() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Workflow 5"
        title="CRM Hygiene"
        description="Read-only CRM hygiene scoring for missing data, stale activity, risky deals, pending reviews, and required rep actions."
        badge={<StatusBadge status="ready" />}
      />
      <section className="twoColumn">
        <DetailCard label="Current behavior" title="Deal risk monitor">
          <p>
            The backend checks owner, next step, activity recency, proposal
            status, review status, required fields, open risks, and days in
            stage.
          </p>
        </DetailCard>
        <DetailCard label="Data integrity" title="Read-only guardrail">
          <p>
            This workflow recommends actions and creates review items where
            needed. It does not mutate CRM records automatically.
          </p>
        </DetailCard>
      </section>
    </div>
  );
}
