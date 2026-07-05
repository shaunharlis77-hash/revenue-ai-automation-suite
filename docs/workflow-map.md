# Workflow Map

## Current Workflow Areas

The frontend suite now separates the product into clear operating areas:

- Dashboards: Sales Manager Dashboard, Admin Dashboard, and Overview.
- Workflows: Lead Intake, Lead Scoring, Meeting Summaries, Follow-Up Drafts, Proposal Drafts, CRM Hygiene, and Sales Knowledge Base.
- CRM: CRM Records and HubSpot Status.
- Governance: Review Queue and Audit Trail.
- Operations: Operational Logs and Impact Metrics.

The admin side intentionally keeps three separate views:

- Review Queue: the human decision layer.
- Audit Trail: business and governance traceability.
- Operational Logs: step-level maintenance and failure diagnosis.

CRM Records and HubSpot Status show the CRM/source-of-truth boundary, adapter mode, sync status, safe write-back behavior, and token-safe configuration status.

## Phase 7 Demo Story Flow

Phase 7 completes the interview demo by following one lead from first touch to pipeline management.

The demo story now covers:

1. A lead enters through Lead Intake.
2. The backend enriches, scores, routes, and writes safe CRM fields.
3. A meeting is attached to the CRM record.
4. Meeting notes are summarized into a CRM-ready note and next-step plan.
5. Review-required actions create review items.
6. A follow-up draft is prepared and approved through the Review Queue.
7. Approval writes a CRM activity and keeps the draft customer-facing but unsent.
8. Follow-up outcome is captured and written back as CRM activity.
9. A proposal/package outline is prepared, approved, and recorded as CRM activity.
10. CRM hygiene checks the deal for stale activity, missing owner, missing next step, and risk.
11. Risky items create review visibility.
12. Review-required items create safe notification events for the assigned owner, routed rep, or manager fallback.
13. Failed workflow steps create safe notification events for admin/ops.
14. Dashboards use persisted workflow, audit, review, CRM, activity, step, and notification records.

FastAPI remains the decisioning layer. HubSpot or the mock CRM adapter remains the source of truth for CRM-style records and activity. n8n orchestrates incoming webhooks, review approvals, scheduled hygiene checks, demo setup, and failure notifications.

## n8n Orchestration

Importable n8n workflow JSON files live in `workflows/n8n/`.

The current exports are:

- `lead-intake-to-api.json`.
- `meeting-completed-to-summary.json`.
- `review-approved-crm-writeback.json`.
- `weekly-crm-hygiene.json`.
- `workflow-failure-notification.json`.
- `full-demo-story-orchestrator.json`.

n8n should call the backend API and pass event payloads. It should not own scoring, summarization, routing, review policy, CRM writeback policy, audit trail, or operational diagnostics.

## Notification Rules

Notifications are durable local records and may be sent to n8n only when `N8N_FAILURE_WEBHOOK_URL` is configured.

- Review items with an assigned owner or routed rep create `review_required` notifications for that owner/rep.
- Review items without an assigned owner create `review_assignment_needed` notifications for the manager.
- Risky sales items without an owner use manager fallback and recommend assigning an owner.
- Failed workflow steps create `workflow_step_failed` notifications for admin/ops.
- Notification records must not include secrets, webhook URLs, HubSpot tokens, or private credentials.
- Review notifications create audit events and workflow step events.
- Manager fallback notifications create explicit `manager_fallback_notification_created` audit events.

## Future Workflow Pattern

Each future workflow should follow a predictable pattern:

1. Collect context from approved sources.
2. Validate inputs and permissions.
3. Generate or calculate a draft output.
4. Show the output to a human reviewer.
5. Capture edits, approval, or rejection.
6. Take the approved action.
7. Log the result.

## Non-Negotiable Audit And Observability Layer

Every workflow, adapter, automation, and integration going forward must include both a business audit trail and operational observability. These are acceptance criteria, not optional future work.

The business audit trail must capture:

- Business event.
- Workflow name.
- Affected entity.
- Decision or action taken.
- Applied, blocked, skipped, failed, or recommended status.
- Guardrail status.
- Review requirement.
- No secrets.

Operational observability must capture:

- Technical step name.
- Step status.
- Severity.
- Error type.
- Safe error message.
- Retryable true or false.
- Recommended fix.
- Useful debug metadata.
- No secrets.

A workflow is not considered complete unless:

- Functional behavior works.
- Tests pass.
- Audit events are written.
- Operational step events are written.
- Failures are diagnosed cleanly.
- Human-review policy is explicit where relevant.
- `docs/build-log.md` is updated.
- `docs/workflow-map.md` is updated if routes, workflows, or entities changed.
- `docs/interview-explanation.md` is updated if the demo story changed.

## Workflow 1: Lead Scoring and Routing

### What the workflow does

Lead Scoring and Routing reviews a new inbound lead and produces a simple recommendation: how strong the lead looks, why it received that score, and where it should go next.

### Which sales rep task it removes

It reduces the manual first-pass sorting that reps and revenue operations teams do when they read form submissions, check fit, judge urgency, and decide who should follow up.

### Which AI GTM Engineer role requirements it addresses

This workflow maps to practical AI GTM work because it combines sales process understanding, structured data design, workflow thinking, human review, CRM awareness, and measurable business impact.

### What data it needs

The first version uses `sample-data/leads.json` as a small golden test dataset. It has 8 carefully chosen synthetic leads so the scoring logic can be tested and explained clearly.

A larger demo dataset of 30-40 leads will be added later for dashboard realism and volume testing. The larger dataset does not need hand-written expected results for every lead.

The golden dataset includes:

- Lead identity and company.
- Role or persona.
- Company size.
- Lead source.
- Submitted message.
- Timeline.
- Budget signal.
- Current CRM.
- Created date.

### What it outputs

The workflow should eventually output:

- Lead score.
- Priority.
- Persona.
- Pain points.
- Urgency.
- Recommended route.
- Next best action.
- Confidence.
- Human review flag.
- Short reasoning.

### What should be automated now

For the design stage, only sample data and expected scoring results are defined. The future first build should use simple deterministic rules against synthetic data before any AI or CRM integration is added.

### What should require human review

Human review should be required for enterprise leads with missing information, urgent implementation requests, low-confidence recommendations, spam-like submissions, and any future action that would change CRM ownership, lifecycle stage, or customer-facing communication.

### What future HubSpot/n8n integration will do

HubSpot may eventually provide real lead records and receive approved scoring or routing updates. n8n may eventually trigger the workflow when a lead is created, notify the right team, and coordinate review steps. Neither tool is connected in the design foundation.

## Workflow 2: Meeting Capture and CRM Summary

### What the workflow does

Meeting Capture and CRM Summary turns meeting content into a structured CRM-ready summary and a next-step action plan. It helps capture pain points, objections, buying signals, next steps, follow-up timing, recommended actions, and whether human review is needed.

This workflow has two stages:

1. Meeting Capture / Minutes Agent.
2. Meeting Summary to CRM Update.

### Where the meeting summary/minutes come from

For the prototype, meeting content comes from synthetic sample transcripts, meeting minutes, or rough notes.

In a real implementation, the capture layer could receive transcripts or minutes from Microsoft Teams, Google Meet, Zoom, or another meeting notes tool. The summary workflow should not depend on one meeting platform.

### Which sales rep task it removes

It reduces post-call admin for reps: writing CRM notes, remembering next steps, logging objections, and deciding what needs follow-up.

### Which AI GTM Engineer role requirements it addresses

This workflow maps to AI GTM work because it combines sales process knowledge, structured extraction, CRM readiness, human review, meeting-tool awareness, and workflow observability.

### What data it needs

The design foundation uses `sample-data/meeting-transcripts.json` with:

- Meeting ID.
- Lead ID.
- Deal ID.
- Rep and contact names.
- Company.
- Meeting date.
- Meeting source.
- Source platform.
- Transcript type.
- Transcript, minutes, or rough notes.

### What it outputs

The workflow should eventually output:

- CRM note.
- Pain points.
- Objections.
- Buying signals.
- Next steps.
- Recommended actions.
- Follow-up due timing.
- Deal stage recommendation.
- Proposal needed flag.
- Confidence.
- Human review flag.
- Needs more information flag.
- Short reasoning.

### What should be automated now

For the design stage, only sample meeting content and expected summary results are defined. The future first build should use deterministic extraction against synthetic data before any LLM, CRM, or meeting-platform integration is added.

The workflow should save rep time even when review is required. Review means the rep approves prepared work, such as a CRM note, follow-up task, draft follow-up, or review item. It does not mean the rep starts from zero.

### What should require human review

Human review should be required for customer-facing follow-ups, proposal drafts, deal stage changes, low-confidence summaries, missing-information cases, poor transcripts, pricing concerns, legal or security issues, and implementation-risk discussions.

### What future HubSpot/n8n integration will do

HubSpot may eventually provide lead and deal context and receive approved CRM notes or updates. n8n may eventually trigger the summary workflow after meeting content is available, notify the rep, create review tasks, and coordinate approved CRM updates.

### What future Teams/Google Meet/Zoom integration could do

Meeting platforms may eventually provide transcripts, meeting minutes, participant details, and meeting timestamps. The platform layer should feed content into the workflow without changing the summary rules.

### What observability should track

Observability should track whether capture ran, whether summary extraction ran, whether review was required, whether CRM was left unchanged, where failures happened, and what the rep should do next.

## Workflow 3: Follow-Up Drafting

### What the workflow does

Follow-Up Drafting prepares a customer-facing follow-up message for sales rep review. It uses structured meeting and lead context to draft a simple message, explain why review is required, and identify any risk-sensitive topics.

### Which sales rep task it removes

It reduces the time reps spend writing first-draft follow-ups after meetings. The rep still reviews and approves the message before anything is sent.

### Which AI GTM Engineer role requirements it addresses

This workflow maps to AI GTM work because it combines customer-facing communication, sales context, risk controls, human review, and workflow observability.

### What data it needs

The first version uses `sample-data/follow-up-inputs.json` with:

- Follow-up ID.
- Lead and meeting IDs.
- Rep, contact, and company names.
- Lead priority and deal stage recommendation.
- Pain points, objections, buying signals, and next steps.
- Follow-up timing.
- Message channel and tone.

### What it outputs

The workflow outputs:

- Draft subject and body.
- Message channel and tone.
- Source context summary.
- Review required flag.
- Review reasons and risk notes.
- Recommended send timing.
- Next action.
- Confidence.
- Reasoning.

### What should be automated now

The workflow may prepare a draft, prepare review notes, and log the workflow result. It does not send messages, update CRM records, or call external tools.

### What should require human review

Human review is always required because this workflow creates customer-facing copy. Pricing, legal, security, implementation, adoption risk, and missing next-step cases need extra review attention.

### What future HubSpot/n8n integration will do

HubSpot may eventually provide approved contact, meeting, and deal context and store reviewed follow-up drafts. n8n may eventually trigger draft creation after a meeting summary is complete and route the draft into a review queue.

### What observability should track

Observability should track whether the draft workflow ran, whether it succeeded or failed, which follow-up input was used, whether review is required, what the rep should do next, and why any failure happened.

## Workflow 4: Proposal / Package Outline Drafting

### What the workflow does

Proposal / Package Outline Drafting prepares an internal proposal or package outline for sales rep review. It turns discovery context into a structured outline, but it does not create a final customer-ready proposal.

### Which sales rep task it removes

It reduces the manual work of organizing pain points, scope ideas, assumptions, exclusions, risks, and next steps before a rep or manager reviews a package recommendation.

### Which AI GTM Engineer role requirements it addresses

This workflow maps to AI GTM work because it combines sales process understanding, proposal guardrails, risk controls, human review, data integrity, and workflow observability.

### What data it needs

The first version uses `sample-data/proposal-inputs.json` with:

- Proposal ID.
- Lead, meeting, and follow-up IDs.
- Rep, contact, and company names.
- Deal stage recommendation and lead priority.
- Pain points, objections, buying signals, and next steps.
- Requested package type.
- Budget context.
- Implementation timeline.
- Current CRM.
- Risk areas.

### What it outputs

The workflow outputs:

- Proposal title.
- Executive summary.
- Problem statement.
- Recommended package.
- Scope items.
- Implementation considerations.
- Assumptions.
- Exclusions.
- Risk notes.
- Review reasons.
- Confidence.
- Human review flag.
- Next action.
- Reasoning.

### What should be automated now

The workflow may prepare an internal outline, identify risks, recommend a next action, and log the result. It does not send proposals, create final quotes, update CRM records, or call external tools.

### What should require human review

Human review is always required because proposal work can become customer-facing. Pricing, budget, legal, security, implementation, adoption, urgent timeline, and missing-scope cases need extra review attention.

### What future HubSpot/n8n integration will do

HubSpot may eventually provide approved deal context and store reviewed proposal notes. n8n may eventually trigger outline drafting after review-ready meeting context is available and route the outline into a human approval queue.

### What observability should track

Observability should track whether the outline workflow ran, whether it succeeded or failed, which proposal input was used, whether review is required, what the rep should do next, and why any failure happened.

## Workflow 5: CRM Hygiene / Deal Risk Monitor

### What the workflow does

CRM Hygiene / Deal Risk Monitor checks CRM and deal records for missing information, stale activity, risky deal conditions, and required rep actions.

It does not update CRM records automatically. It identifies issues, recommends actions, and flags records that need review.

### Which sales rep task it removes

It reduces the manual work of scanning CRM records for missing owners, missing next steps, stale activity, overdue follow-up, pending proposal review, and incomplete required fields.

### Which AI GTM Engineer role requirements it addresses

This workflow maps to AI GTM work because it combines CRM data quality, pipeline risk monitoring, human review, observability, and practical RevOps controls.

### What data it needs

The first version uses `sample-data/crm-hygiene-inputs.json` with:

- Record, lead, and deal IDs.
- Company and contact names.
- Deal stage and lead priority.
- Owner.
- Last activity date.
- Next step and follow-up timing.
- Proposal and human review status.
- Required CRM fields.
- Open risks.
- Days in stage.
- Deal value band.

### What it outputs

The workflow outputs:

- Hygiene score.
- Risk level.
- Issues.
- Missing fields.
- Stale activity flag.
- Recommended actions.
- Human review flag.
- Next action.
- Confidence.
- Reasoning.

### What should be automated now

The workflow may inspect sample CRM-style data, identify issues, recommend actions, and log the workflow result. It does not update CRM records, assign owners, change deal stages, or call external tools.

### What should require human review

Human review is required for high-risk or critical records, pending proposals with incomplete review, missing owners, and records with multiple serious hygiene issues.

### What future HubSpot/n8n integration will do

HubSpot may eventually provide real CRM records and receive approved cleanup actions. n8n may eventually trigger hygiene checks on a schedule, notify owners, and route high-risk records into a review queue.

### What observability should track

Observability should track whether the hygiene check ran, whether it succeeded or failed, which CRM record was checked, whether review is required, what the owner should do next, and why any failure happened.

## Phase 3: Lead Intake and Enrichment

### What the workflow does

Lead Intake and Enrichment starts the demo from the moment a new lead comes in. It accepts lead details, enriches them with deterministic rules, scores and routes the lead, and writes safe structured fields to an internal CRM-style record.

### Automation policy

Clean leads can be enriched, scored, routed, and written automatically. High-priority leads can also be written automatically, but they create a review item for visibility and quality control. Risky, suspicious, low-confidence, or ambiguous leads can still get safe fields written, but sensitive routing/status actions are blocked pending review.

### What data it needs

The workflow uses basic lead intake data such as contact name, email, company, title, company size, industry, region, source, message, pain points, urgency, budget context, demo request flag, CRM system, and notes.

### What it outputs

The workflow outputs enrichment details, lead score, priority, confidence, urgency, recommended route, next best action, CRM update status, review visibility, audit events, workflow step events, and an internal CRM-style lead record.

### Human review rules

Review is created for high-priority leads, high-risk leads, low-confidence leads, suspicious or test-like leads, ambiguous routing, blocked CRM updates, and missing critical information.

### Future HubSpot/n8n integration

The current version writes only to a local internal CRM-style table. Later, HubSpot can receive approved or safe structured updates, while n8n can trigger lead intake from forms or route notifications. Real integrations are intentionally not connected yet.

## Persistence, Audit Trail, and Review Queue

The backend now has a shared persistence foundation that supports every workflow.

### Workflow runs

Workflow runs are persisted so operators can see what ran, whether it succeeded or failed, whether human review is required, and what should happen next.

### Audit trail

Audit events are append-only. They record workflow events, guardrails, review decisions, actors, entity references, and metadata. There is no delete route for audit events.

### Review queue

Review items are persistent and can be approved or rejected. Approval and rejection update the review item status and create audit events so human decisions remain visible.

### Future role

This foundation keeps the workflow services independent from the database implementation. The current fallback is SQLite for local development, while the service boundary allows future Postgres support without changing workflow logic.

### Workflow integration

Each completed workflow now writes durable audit events. Workflows that require human review also create persistent review items with reviewer context, proposed action, proposed output, risk level, and review reasons.

This keeps workflow execution, guardrails, and human decisions visible without adding CRM write-back or external automation.

## Operational Observability Layer

Operational observability is mandatory for every workflow alongside the audit trail.

`audit_events` are for business and governance traceability. They answer what happened, which guardrails triggered, who approved or rejected something, and whether a CRM update was recommended, blocked, or applied.

`workflow_step_events` are for maintenance and failure diagnosis. They answer which workflow step ran, which step failed, what error happened, whether the failure is retryable, and what a maintainer should check next.

Every existing workflow now records step-level events for its main operational path. Future workflows must include both durable audit events and workflow step events as acceptance criteria before they are considered complete.

## Admin UI Layer

The visible product layer includes Lead Intake, CRM Records, Review Queue, Audit Trail, Operational Logs, Sales Manager Dashboard, and Admin / Operations Dashboard screens.

### Sales Manager Dashboard

The Sales Manager Dashboard is business-facing. It translates AI workflow usage into sales execution signals: lead volume, high-priority leads, CRM update outcomes, open review work, follow-up and proposal assistance, estimated time saved, drop-off zones, AI adoption, and sales execution risks.

It intentionally avoids raw technical diagnostics. If an operational issue affects sales outcomes, it is summarized in manager language, such as CRM sync needs attention, proposal waiting for review, or records missing next steps.

The dashboard uses persisted backend data. If rep-level attribution, follow-up due dates, or stage-level linkage is not available yet, the API returns `not_enough_data` instead of inventing metrics.

### Admin / Operations Dashboard

The Admin / Operations Dashboard is diagnostic. It shows adapter mode, HubSpot configuration status, workflow run health, review queue health, audit health, operational step health, HubSpot sync health, workflow health, recent failures, recommended fixes, and quick links to the operational views.

This dashboard is where RevOps admins and system maintainers should look for failures, guardrails, retryability, sync errors, and maintenance actions.

The Lead Intake screen lets a user submit a synthetic inbound lead and see enrichment, scoring, routing, CRM update status, and review visibility.

The CRM Records screen shows the local mock CRM adapter output. It displays safe CRM-style lead fields, update status, review visibility, risk flags, and related CRM activities.

The Review Queue lets a reviewer see prepared workflow outputs, understand why review is required, and approve or reject pending items.

The Audit Trail shows durable workflow events, guardrail triggers, review decisions, and CRM update recommendations.

The Operational Logs screen shows workflow step events for maintenance. It helps a system owner see which step ran, which step failed, why it failed, whether it is retryable, and what to check next.

This layer is intentionally simple and internal. It does not add authentication yet, and dashboards do not require HubSpot to be enabled.

## Mock CRM Adapter Layer

The CRM adapter layer is the boundary between workflow logic and CRM-style persistence.

Lead Intake calls the selected adapter to create or update safe CRM records. In mock mode, the adapter writes only to local SQLite tables. In HubSpot mode, the adapter can sync safe fields to a HubSpot sandbox using a private app token from environment variables.

The adapter records activity history, audit events, and operational step events so the system owner can see what was written, blocked, synced, or failed.

This keeps workflow code from depending directly on HubSpot implementation details. The same safe-update policy applies in both modes:

- Clean safe updates can be applied.
- High-priority updates can be applied with review visibility.
- Risky or ambiguous updates are blocked pending review.

HubSpot mode also tracks contact, company, deal, task, and note IDs, sync status, last sync time, and sync errors on the local CRM record so the admin UI can diagnose what happened.

## HubSpot Sandbox Adapter Layer

Phase 5 verified the optional HubSpot sandbox adapter behind the same CRM adapter boundary. Mock mode remains the default and local tests force mock mode when they are not explicitly testing HubSpot.

HubSpot mode is enabled only through environment variables. The adapter can sync safe Lead Intake outputs to HubSpot contacts, companies, deals, internal tasks, and internal notes. It also syncs AI custom properties for lead score, priority, route, confidence, next action, human review requirement, workflow run id, and risk level.

The adapter normalizes HubSpot standard fields before sync. Industry values are mapped to HubSpot-safe enum values, and company size ranges are mapped to integer employee counts for `numberofemployees`.

Task payloads include required HubSpot task fields such as timestamp, subject, body, status, priority, and task type. Tasks and notes are useful activity records, but they are not part of the critical sync path. If optional activity creation fails, contact, company, and deal sync can still be preserved as a clean partial sync with audit and operational diagnostics.

Only `scripts/smoke_test_hubspot_sandbox.py` intentionally writes to HubSpot. Mapping and configuration tests do not perform network calls. Tokens are never returned, printed, or logged.

## n8n Role

n8n may eventually trigger workflows, call the FastAPI backend, pass data between systems, and coordinate notifications. n8n should not bypass human review for high-impact actions.

## FastAPI Role

FastAPI should own validation, service boundaries, integration logic, and API contracts.

## Next.js Role

Next.js should provide the user interface for reviewing work, monitoring status, and understanding impact.
