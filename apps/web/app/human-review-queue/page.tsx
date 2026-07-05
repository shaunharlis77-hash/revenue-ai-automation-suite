import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { queueItems } from "@/lib/placeholders";

export default function HumanReviewQueuePage() {
  return (
    <div className="pageStack">
      <PageHeader
        title="Human Review Queue"
        description="Placeholder space for approvals before customer communication, CRM updates, and operational decisions."
        badge={<StatusBadge status="review" />}
      />
      <section className="card detailPanel">
        {queueItems.map((item) => (
          <p key={item}>{item}</p>
        ))}
      </section>
    </div>
  );
}

