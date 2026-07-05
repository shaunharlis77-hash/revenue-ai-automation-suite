import { StatusBadge } from "@/components/StatusBadge";

type WorkflowCardProps = {
  title: string;
  status: "planned" | "review" | "draft" | "ready";
  description: string;
};

export function WorkflowCard({ title, status, description }: WorkflowCardProps) {
  return (
    <article className="workflowCard">
      <div className="workflowTopline">
        <h2 className="workflowTitle">{title}</h2>
        <StatusBadge status={status} />
      </div>
      <p className="workflowDescription">{description}</p>
    </article>
  );
}

