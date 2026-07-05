type DetailCardProps = {
  label?: string;
  title: string;
  children: React.ReactNode;
  className?: string;
};

export function DetailCard({
  label,
  title,
  children,
  className = "",
}: DetailCardProps) {
  return (
    <section className={`card detailPanel detailCard ${className}`}>
      {label ? <p className="cardLabel">{label}</p> : null}
      <h2 className="sectionTitle">{title}</h2>
      <div className="detailCardBody">{children}</div>
    </section>
  );
}
