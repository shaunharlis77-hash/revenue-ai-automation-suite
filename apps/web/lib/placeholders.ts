export const overviewMetrics = [
  {
    label: "Placeholder Workflows",
    value: "9",
    note: "Planned sales operations areas, not active automations.",
  },
  {
    label: "Review Required",
    value: "100%",
    note: "Future AI outputs should route through human approval.",
  },
  {
    label: "External API Calls",
    value: "0",
    note: "This foundation does not connect to live systems.",
  },
  {
    label: "CRM Writes",
    value: "0",
    note: "HubSpot write-back is intentionally not implemented yet.",
  },
];

export const workflowCards = [
  {
    title: "Lead Scoring",
    status: "planned",
    description:
      "Future scoring support for prioritizing sales follow-up using transparent signals.",
  },
  {
    title: "Meeting Summaries",
    status: "draft",
    description:
      "Future summary workspace for sales calls, next steps, and customer context.",
  },
  {
    title: "Follow-Up Drafts",
    status: "review",
    description:
      "Future assisted drafting with human approval before anything reaches a customer.",
  },
  {
    title: "CRM Hygiene",
    status: "planned",
    description:
      "Future checks for stale fields, missing lifecycle data, and duplicate cleanup.",
  },
  {
    title: "Proposal Drafts",
    status: "draft",
    description:
      "Future proposal support using approved messaging and deal context.",
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
