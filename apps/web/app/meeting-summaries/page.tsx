import { DetailCard } from "@/components/DetailCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function MeetingSummariesPage() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Workflow 2"
        title="Meeting Summaries"
        description="CRM-ready meeting notes, objections, buying signals, next steps, and review-required action plans."
        badge={<StatusBadge status="ready" />}
      />
      <section className="twoColumn">
        <DetailCard label="Current behavior" title="Structured summary output">
          <p>
            Meeting content is turned into a CRM note, pain points, objections,
            buying signals, next steps, confidence, and recommended actions.
          </p>
        </DetailCard>
        <DetailCard label="Review policy" title="Approval gate, not waiting room">
          <p>
            Internal notes and tasks can be prepared, while customer-facing
            follow-ups, deal-stage recommendations, proposal outlines, and risky
            claims require review.
          </p>
        </DetailCard>
      </section>
    </div>
  );
}
