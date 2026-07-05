import { DetailCard } from "@/components/DetailCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { queueItems } from "@/lib/placeholders";

export default function HumanReviewQueuePage() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Governance"
        title="Human Review Queue"
        description="Legacy placeholder for the human decision layer. Use the live Review Queue for persisted review items."
        badge={<StatusBadge status="review" />}
      />
      <DetailCard label="Review policy" title="What requires approval">
        {queueItems.map((item) => (
          <p key={item}>{item}</p>
        ))}
      </DetailCard>
    </div>
  );
}
