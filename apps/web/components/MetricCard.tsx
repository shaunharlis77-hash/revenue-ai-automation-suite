type MetricCardProps = {
  label: string;
  value: string;
  note: string;
};

export function MetricCard({ label, value, note }: MetricCardProps) {
  return (
    <article className="metricCard">
      <p className="metricLabel">{label}</p>
      <p className="metricValue">{value}</p>
      <p className="metricNote">{note}</p>
    </article>
  );
}

