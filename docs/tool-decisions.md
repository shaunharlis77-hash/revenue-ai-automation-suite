# Tool Decisions

## Next.js

### Role in the architecture

Next.js provides the internal sales operations dashboard. It is the place where users will eventually review AI-assisted work, inspect workflow status, approve or reject suggested actions, and monitor operational impact.

### Why it was chosen

Next.js was chosen because it supports TypeScript, clear file-based routing through the App Router, reusable UI components, and a strong foundation for interactive internal tools.

### Fit for AI GTM and sales automation

Sales automation needs a review surface, not only background jobs. Next.js fits because future workflows can expose lead scores, meeting summaries, follow-up drafts, CRM hygiene issues, proposal drafts, knowledge answers, metrics, and review queues in one usable interface.

### Alternatives considered or avoided

A simple static site was avoided because the project will likely need dynamic state, workflow review screens, and authenticated internal workflows later. A heavier enterprise frontend stack was avoided because the current foundation should stay easy to understand and iterate on.

## FastAPI

### Role in the architecture

FastAPI provides the backend API layer. It will eventually own validation, workflow-facing endpoints, service boundaries, integration logic, and contracts between the web dashboard, n8n, HubSpot, and AI services.

### Why it was chosen

FastAPI was chosen because it is simple, typed, well documented, and well suited to clean API development. It also works naturally with Pydantic models, which helps keep request and response shapes explicit.

### Fit for AI GTM and sales automation

AI GTM workflows need predictable backend boundaries. FastAPI can expose endpoints for lead scoring, meeting summaries, follow-up drafts, CRM hygiene checks, proposal drafting, sales knowledge base questions, logs, and metrics while keeping business rules centralized.

### Alternatives considered or avoided

Flask was avoided because FastAPI gives stronger typing and API documentation defaults. A large backend framework was avoided because the project does not need that complexity at the foundation stage.

## pydantic-settings

### Role in the architecture

`pydantic-settings` handles environment-based configuration for the FastAPI app.

### Why it was chosen

It was chosen because settings can be declared as typed fields and loaded from environment variables or local `.env` files without hard-coding values in the application.

### Fit for AI GTM and sales automation

Future sales automation work will likely need separate configuration for local development, test data, staging integrations, production integrations, feature flags, and provider settings. Typed configuration helps keep those boundaries clear.

### Alternatives considered or avoided

Hard-coded settings were intentionally avoided. Custom environment parsing was avoided because `pydantic-settings` already solves the problem cleanly.

## n8n

### Role in the architecture

n8n is planned as the workflow automation layer. It may eventually coordinate triggers, scheduled jobs, webhooks, notifications, and handoffs between systems.

### Why it was chosen

n8n was chosen because it is understandable for operations teams, can make workflow steps visible, and can connect systems without every workflow becoming custom backend code.

### Fit for AI GTM and sales automation

Sales automation often depends on event-driven work: a new lead arrives, a meeting ends, a CRM field changes, or a review is approved. n8n can coordinate those flows while FastAPI handles validation and business rules.

### Alternatives considered or avoided

Fully custom workflow orchestration was avoided at this stage because it can hide simple business processes inside code. Black-box automation was also avoided because human operators should be able to inspect and reason about workflow steps.

## HubSpot

### Role in the architecture

HubSpot is planned as the CRM system of record for contacts, companies, deals, activities, and sales process data.

### Why it was chosen

HubSpot was chosen because it is a common GTM platform and a natural source of sales context for lead prioritization, CRM hygiene, meeting follow-up, and reporting workflows.

### Fit for AI GTM and sales automation

AI sales workflows become more useful when grounded in CRM context. HubSpot can eventually provide deal stage, lifecycle state, ownership, activity history, and engagement data. Any write-back should be controlled and reviewable.

### Alternatives considered or avoided

Generic CRM abstraction was avoided for the foundation because it can add complexity before the first real integration exists. Direct automated CRM writes are intentionally avoided until review policy, audit logging, and permissions are designed.

## AI Services

### Role in the architecture

AI services are planned as assistive capabilities behind specific workflows. They may eventually help summarize meetings, draft follow-ups, classify CRM hygiene issues, suggest lead scoring signals, draft proposal content, and answer sales knowledge questions.

### Why they were chosen

AI services are useful for language-heavy and pattern-recognition tasks that slow down sales teams when done manually. They can turn raw context into drafts, summaries, and recommendations.

### Fit for AI GTM and sales automation

GTM teams spend significant time on repetitive writing, research, cleanup, and synthesis. AI can reduce that effort when outputs are grounded in approved context and reviewed by humans.

### Alternatives considered or avoided

Fully autonomous AI agents are intentionally avoided at this stage. Rule-based automation remains useful and should be preferred where deterministic logic is enough. AI should be added only where it improves the workflow without weakening control.

## Markdown Knowledge Base

### Role in the architecture

The Markdown knowledge base will hold approved sales content, process notes, objection handling, positioning, and enablement material.

### Why it was chosen

Markdown is simple, versionable, easy to review in pull requests, and readable without special tools.

### Fit for AI GTM and sales automation

Future AI workflows need trusted source material. A Markdown knowledge base can become a clean starting point for retrieval, citations, sales answers, and approved messaging.

### Alternatives considered or avoided

A database-backed knowledge system was avoided for the foundation because it would add setup work before the content model is clear. Unstructured document dumps were avoided because they make review and source control harder.

## SOP Documentation

### Role in the architecture

SOP documentation explains how people should operate, review, maintain, and improve the automation system.

### Why it was chosen

Sales AI automation is partly a process design problem. SOPs make responsibilities, handoffs, and review standards explicit.

### Fit for AI GTM and sales automation

Human review, CRM hygiene, follow-up approvals, and workflow exception handling all need clear operating procedures. SOPs help make the system usable by a team, not only by its builder.

### Alternatives considered or avoided

Relying on informal team knowledge was avoided because it creates inconsistent review and poor handoffs. Overly formal process tooling was avoided until the actual workflows mature.

## Audit Logging

### Role in the architecture

Audit logging will record important workflow actions, especially AI-assisted suggestions, review decisions, approvals, rejections, and future CRM write-back attempts.

Audit logging is part of observability and maintenance, not just record keeping. It should help operators understand workflow health, failure points, review decisions, and the history of suggested or completed updates.

### Why it was chosen

Audit logs create accountability and help teams understand what happened when automation participates in revenue workflows.

### Fit for AI GTM and sales automation

Sales automation affects customer communication and CRM data quality. Audit logging helps reviewers trace who approved an action, what changed, and whether the automation performed as expected.

### Alternatives considered or avoided

No logging was avoided because it would make AI-assisted work hard to trust. Logging every low-level implementation detail is also avoided for now because the foundation only needs clear future intent and placeholder endpoints.
