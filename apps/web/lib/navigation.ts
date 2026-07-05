export type NavigationItem = {
  label: string;
  href: string;
};

export type NavigationGroup = {
  label: string;
  items: NavigationItem[];
};

export const navigationGroups: NavigationGroup[] = [
  {
    label: "Dashboards",
    items: [
      { label: "Sales Manager Dashboard", href: "/dashboard" },
      { label: "Admin Dashboard", href: "/admin-dashboard" },
      { label: "Overview", href: "/" },
    ],
  },
  {
    label: "Workflows",
    items: [
      { label: "Lead Intake", href: "/lead-intake" },
      { label: "Lead Scoring", href: "/lead-scoring" },
      { label: "Meeting Summaries", href: "/meeting-summaries" },
      { label: "Follow-Up Drafts", href: "/follow-up-drafts" },
      { label: "Proposal Drafts", href: "/proposal-drafts" },
      { label: "CRM Hygiene", href: "/crm-hygiene" },
      { label: "Sales Knowledge Base", href: "/sales-knowledge-base" },
    ],
  },
  {
    label: "CRM",
    items: [
      { label: "CRM Records", href: "/crm-records" },
      { label: "HubSpot Status", href: "/hubspot-status" },
    ],
  },
  {
    label: "Governance",
    items: [
      { label: "Review Queue", href: "/review-queue" },
      { label: "Audit Trail", href: "/audit-trail" },
    ],
  },
  {
    label: "Operations",
    items: [
      { label: "Operational Logs", href: "/operational-logs" },
      { label: "Impact Metrics", href: "/impact-metrics" },
    ],
  },
];

export const navigationItems = navigationGroups.flatMap((group) => group.items);
