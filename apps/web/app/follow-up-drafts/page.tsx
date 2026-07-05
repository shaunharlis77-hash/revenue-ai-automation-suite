import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function FollowUpDraftsPage() {
  return (
    <div className="pageStack">
      <PageHeader
        title="Follow-Up Drafts"
        description="Placeholder space for future sales email drafts that require human approval before sending."
        badge={<StatusBadge status="review" />}
      />
      <section className="card detailPanel">
        <p>
          Future drafts should cite the source context used and remain editable
          before any customer-facing action.
        </p>
      </section>
    </div>
  );
}

