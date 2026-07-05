import { PageHeader } from "@/components/PageHeader";
import { LoadingState } from "@/components/LoadingState";
import { StatusBadge } from "@/components/StatusBadge";

export default function OperationalLogsLoading() {
  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Admin"
        title="Operational Logs"
        description="Step-level workflow observability for failures, retries, and maintenance."
        badge={<StatusBadge status="ready" />}
      />
      <LoadingState
        title="Loading operational logs"
        message="Fetching step-level workflow diagnostics."
      />
    </div>
  );
}
