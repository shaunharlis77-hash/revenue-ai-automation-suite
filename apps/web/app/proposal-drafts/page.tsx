import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";

export default function ProposalDraftsPage() {
  return (
    <div className="pageStack">
      <PageHeader
        title="Proposal Drafts"
        description="Placeholder space for future proposal outlines, approved positioning, and deal-specific recommendations."
        badge={<StatusBadge status="draft" />}
      />
      <section className="card detailPanel">
        <p>
          Future proposal support should use approved sales language and keep
          pricing, legal, and contractual details under human control.
        </p>
      </section>
    </div>
  );
}

