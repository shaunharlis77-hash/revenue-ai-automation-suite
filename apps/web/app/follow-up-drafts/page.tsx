import { DetailCard } from "@/components/DetailCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function FollowUpDraftsPage() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Workflow 3"
        title="Follow-Up Drafts"
        description="Customer-facing follow-up drafts prepared from approved meeting context and always routed for human review."
        badge={<StatusBadge status="ready" />}
      />
      <section className="twoColumn">
        <DetailCard label="Customer-facing control" title="Draft only">
          <p>
            The workflow can prepare a subject, body, source summary, risk notes,
            review reasons, and recommended timing. It never sends the message.
          </p>
        </DetailCard>
        <DetailCard label="Safety language" title="No unsafe promises">
          <p>
            Drafts avoid guarantees, legal approval claims, full-security claims,
            and definite implementation promises.
          </p>
        </DetailCard>
      </section>
    </div>
  );
}
