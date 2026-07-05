type StatusTone = "planned" | "review" | "draft" | "ready";

type StatusBadgeProps = {
  status: StatusTone;
};

const labels: Record<StatusTone, string> = {
  planned: "Planned",
  review: "Needs Review",
  draft: "Draft",
  ready: "Ready",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`statusBadge ${status}`}>{labels[status]}</span>;
}

