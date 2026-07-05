type ErrorStateProps = {
  title?: string;
  message: string;
  detail?: string;
};

export function ErrorState({
  title = "Backend unavailable",
  message,
  detail,
}: ErrorStateProps) {
  return (
    <section className="card statePanel errorState">
      <span className="stateIcon" aria-hidden="true" />
      <div>
        <p className="cardLabel">{title}</p>
        <p>{message}</p>
        {detail ? <p className="safeDetail">{detail}</p> : null}
      </div>
    </section>
  );
}
