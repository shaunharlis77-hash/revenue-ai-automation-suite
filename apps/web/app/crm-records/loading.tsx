import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";


export default function CRMRecordsLoading() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Phase 4"
        title="CRM Records"
        description="Loading mock CRM adapter records and activity history."
        badge={<StatusBadge status="draft" />}
      />
      <LoadingState
        title="Loading CRM records"
        message="Fetching internal CRM-style records and activity history."
      />
    </div>
  );
}
