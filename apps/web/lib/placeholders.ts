export const overviewMetrics = [
  {
    label: "Backend workflows",
    value: "5",
    note: "Deterministic workflows with audit and operational logs.",
  },
  {
    label: "Human review layer",
    value: "Live",
    note: "Review queue supports approval and rejection decisions.",
  },
  {
    label: "CRM adapter",
    value: "Mock/HubSpot",
    note: "Mock remains safe by default; HubSpot sandbox is env controlled.",
  },
  {
    label: "Guardrails",
    value: "Required",
    note: "Audit trail and operational logs are mandatory for workflows.",
  },
];

export const workflowCards = [
  {
    title: "Lead Scoring",
    status: "ready",
    description:
      "Deterministic scoring support for prioritizing sales follow-up using transparent signals.",
  },
  {
    title: "Meeting Summaries",
    status: "ready",
    description:
      "Structured summary workspace for sales calls, next steps, and customer context.",
  },
  {
    title: "Follow-Up Drafts",
    status: "ready",
    description:
      "Assisted drafting with human approval before anything reaches a customer.",
  },
  {
    title: "CRM Hygiene",
    status: "ready",
    description:
      "Read-only checks for stale fields, missing lifecycle data, and deal risk.",
  },
  {
    title: "Proposal Drafts",
    status: "ready",
    description:
      "Proposal outline support using approved guardrails and deal context.",
  },
  {
    title: "Knowledge Base",
    status: "ready",
    description:
      "Starter space for approved sales answers, process notes, and enablement content.",
  },
] as const;

export const queueItems = [
  "Review AI-assisted follow-up before sending",
  "Approve CRM field changes before write-back",
  "Check proposal language against approved positioning",
  "Confirm meeting action items with account owner",
];
