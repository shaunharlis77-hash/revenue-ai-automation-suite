import { LoadingState } from "@/components/LoadingState";

export default function ReviewQueueLoading() {
  return (
    <div className="pageStack">
      <LoadingState
        title="Loading review queue"
        message="Fetching pending, approved, and rejected review items."
      />
    </div>
  );
}
