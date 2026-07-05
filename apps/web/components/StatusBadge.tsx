type StatusTone = "planned" | "review" | "draft" | "ready" | "live";

type StatusBadgeProps = {
  status: StatusTone;
};

const labels: Record<StatusTone, string> = {
  planned: "Planned",
  review: "Needs Review",
  draft: "Draft",
  ready: "Ready",
  live: "Live",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`statusBadge ${status}`}>{labels[status]}</span>;
}
