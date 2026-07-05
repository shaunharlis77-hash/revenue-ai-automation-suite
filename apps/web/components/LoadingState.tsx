type LoadingStateProps = {
  title?: string;
  message?: string;
};

export function LoadingState({
  title = "Loading workspace",
  message = "Fetching the latest operational data.",
}: LoadingStateProps) {
  return (
    <section className="card statePanel loadingState" aria-live="polite">
      <span className="stateIcon" aria-hidden="true" />
      <div>
        <p className="cardLabel">{title}</p>
        <p>{message}</p>
      </div>
    </section>
  );
}
