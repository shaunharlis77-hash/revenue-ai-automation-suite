import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function MeetingSummariesPage() {
  return (
    <div className="pageStack">
      <PageHeader
        title="Meeting Summaries"
        description="Placeholder space for future call summary review, next steps, objections, and customer context."
        badge={<StatusBadge status="draft" />}
      />
      <section className="card detailPanel">
        <p>
          Future summaries should be reviewed by the account owner before they
          are shared or used to update CRM notes.
        </p>
      </section>
    </div>
  );
}

