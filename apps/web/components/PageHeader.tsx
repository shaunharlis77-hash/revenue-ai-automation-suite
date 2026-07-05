type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description: string;
  badge?: React.ReactNode;
};

export function PageHeader({
  eyebrow = "Sales operations",
  title,
  description,
  badge,
}: PageHeaderProps) {
  return (
    <header className="pageHeader">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="pageDescription">{description}</p>
      </div>
      {badge}
    </header>
  );
}

