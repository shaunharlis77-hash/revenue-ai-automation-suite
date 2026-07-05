type MetricCardProps = {
  label: string;
  value: string;
  note: string;
  tone?: "neutral" | "good" | "warning" | "danger" | "review";
};

export function MetricCard({
  label,
  value,
  note,
  tone = "neutral",
}: MetricCardProps) {
  return (
    <article className={`metricCard metric-${tone}`}>
      <p className="metricLabel">{label}</p>
      <p className="metricValue">{value}</p>
      <p className="metricNote">{note}</p>
    </article>
  );
}
