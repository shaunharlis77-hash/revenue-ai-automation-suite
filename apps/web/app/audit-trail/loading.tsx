import { LoadingState } from "@/components/LoadingState";

export default function AuditTrailLoading() {
  return (
    <div className="pageStack">
      <LoadingState
        title="Loading audit trail"
        message="Fetching business and governance events from the API."
      />
    </div>
  );
}
