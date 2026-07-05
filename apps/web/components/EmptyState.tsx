type EmptyStateProps = {
  title: string;
  message: string;
  action?: React.ReactNode;
};

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <section className="card statePanel emptyState">
      <span className="stateIcon" aria-hidden="true" />
      <div>
        <p className="cardLabel">{title}</p>
        <p>{message}</p>
        {action ? <div className="stateAction">{action}</div> : null}
      </div>
    </section>
  );
}
