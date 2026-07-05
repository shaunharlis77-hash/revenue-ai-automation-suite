# revenue-ai-automation-suite

Foundation for a revenue AI automation suite that will eventually support sales operations workflows across a web dashboard, FastAPI backend, n8n automations, HubSpot, and AI-assisted task flows.

This repository is intentionally controlled. Mock/local mode is the default. Optional HubSpot sandbox sync can be enabled with environment variables, but no real secrets are committed and no customer-facing messages are sent automatically.

## What This Project Is

The project is a working foundation for an internal sales operations automation system. The long-term goal is to help revenue teams reduce manual work across lead scoring, meeting summaries, follow-up drafting, CRM hygiene, proposal drafting, knowledge retrieval, impact reporting, and human review.

## Current Status

- Deterministic backend workflows are implemented and tested.
- Review Queue, Audit Trail, Operational Logs, Lead Intake, CRM Records, and HubSpot Status UI layers are available.
- Sales Manager Dashboard and Admin / Operations Dashboard are available.
- The frontend has a suite-wide polish pass with grouped active navigation, consistent page headers, improved dashboard cards, readable tables, and intentional empty/error/loading states.
- Mock CRM adapter remains the default local mode.
- Optional HubSpot sandbox adapter is functionally verified.
- Business audit trail and operational observability are mandatory for every workflow and integration.

## Current Structure

```text
apps/
  api/        FastAPI service foundation
  web/        Next.js TypeScript dashboard foundation
docs/         Plain-language project documentation
sops/         Future operating procedures
knowledge-base/
sample-data/
workflows/
  n8n/        Future n8n workflow exports and notes
```

## Local Setup

### API

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

API endpoints:

```text
POST /intake/lead
GET  /intake/leads
GET  /intake/leads/{lead_id}

POST /ai/score-lead
POST /ai/summarize-meeting
POST /ai/draft-follow-up
POST /ai/check-crm-hygiene
POST /ai/draft-proposal
POST /ai/ask-sales-kb

GET  /logs
GET  /logs/recent
GET  /logs/workflow-steps
POST /logs/ai-action

GET  /audit/events
GET  /review/items
GET  /notifications
GET  /notifications/recent
POST /notifications/test-failure
POST /demo/records/{crm_record_id}/meeting
POST /demo/records/{crm_record_id}/follow-up-outcome
POST /demo/full-story/run
GET  /metrics/dashboard
GET  /metrics/sales-manager-dashboard
GET  /metrics/admin-dashboard
```

`POST /ai/score-lead` now returns deterministic lead scoring output. The remaining `/ai/*`, `/logs`, and `/metrics` endpoints return placeholder JSON only. None of these endpoints call HubSpot, write CRM data, use LLMs, or contact external services.

## Workflow 1: Lead Scoring and Routing

`POST /ai/score-lead` accepts a lead payload and returns deterministic scoring output, including score, priority, persona, pain points, urgency, route, next best action, confidence, human review flag, and reasoning.

The first version uses simple rules only. It scores leads based on intent, urgency, role, company size, CRM context, budget, message content, missing information, and spam or test signals.

Run the local scoring check from the repository root:

```bash
python apps/api/scripts/test_lead_scoring.py
```

Latest verified result:

```text
8 passed, 0 failed
```

The script loads `sample-data/leads.json`, calls the scoring service directly, and compares generated outputs against `sample-data/lead-scoring-expected-results.json`.

Validation rejects blank required fields before scoring.

HubSpot, LLM, n8n, and external API integrations are not connected yet.

## Phase 3: Lead Intake and Enrichment

`POST /intake/lead` accepts a new inbound lead, enriches it with deterministic rules, scores it, recommends routing, and writes safe structured fields to a local CRM-style record.

The workflow uses the existing audit trail, review queue, workflow logs, and operational step events. Clean leads can be applied automatically. High-priority leads are applied with review visibility. Risky, suspicious, low-confidence, or ambiguous leads are blocked pending review for sensitive routing/status actions.

Run the local intake check from `apps/api`:

```bash
python scripts/test_lead_intake.py
```

Frontend page:

```text
http://localhost:3000/lead-intake
```

No real HubSpot, enrichment API, LLM, n8n, email sending, auth, Docker, or Postgres changes are included.

## Workflow 2: Meeting Capture and CRM Summary

`POST /ai/summarize-meeting` accepts meeting content and returns a CRM-ready summary with pain points, objections, buying signals, next steps, follow-up timing, confidence, review flags, and `recommended_actions`.

The first version uses deterministic extraction rules only. It works with manual notes or synthetic sample transcripts and does not depend on any meeting platform.

Run the local meeting summary check from the repository root:

```bash
python apps/api/scripts/test_meeting_summary.py
```

The script loads `sample-data/meeting-transcripts.json`, calls the summary service directly, and compares key output fields against `sample-data/meeting-summary-expected-results.json`.

`recommended_actions` shows how the workflow prepares next steps, such as CRM notes, rep tasks, draft follow-ups, proposal outlines, and review items, instead of only sending everything to review.

Meeting platform, HubSpot, n8n, LLM, and external API integrations are not connected yet.

## Demo Seed Journey

To populate the Review Queue and Audit Trail with synthetic demo data, run:

```bash
cd apps/api
python scripts/seed_demo_journey.py
```

The seed uses existing workflow services to create a Northstar Analytics journey with lead scoring, meeting summary, follow-up draft, proposal outline, CRM hygiene checks, review decisions, audit events, and workflow step events.

Default behavior is append-only. For local demos only, you can reset local persistence first:

```bash
python scripts/seed_demo_journey.py --reset-local-demo
```

After seeding, open:

```text
http://localhost:3000/review-queue
http://localhost:3000/audit-trail
http://localhost:8000/audit/events
http://localhost:8000/review/items
http://localhost:8000/logs/workflow-steps
```

## Phase 7 Full Demo Story

To run the complete interview story from lead intake through meeting summary, follow-up approval, proposal approval, CRM hygiene, audit events, operational logs, review items, and failure notifications:

```bash
cd apps/api
python scripts/run_full_demo_story.py --reset-demo
```

The runner prints a token-safe summary with the demo run id, CRM record id, lead score, route, review item ids, follow-up outcome, proposal status, hygiene status, audit event count, workflow step count, review item count, and notification count.

n8n importable workflow JSON files are in:

```text
workflows/n8n/
```

Set this n8n environment variable when running n8n in Docker on the same machine:

```text
API_BASE_URL=http://host.docker.internal:8000
```

FastAPI remains the business logic layer. n8n orchestrates webhooks, schedules, review approvals, demo setup, and failure notifications.

Notification behavior:

- Review-required work creates notification records for the assigned owner/routed rep, or manager fallback when no owner is available.
- Failed workflow steps create admin/ops notification records.
- Without `N8N_FAILURE_WEBHOOK_URL`, notifications are stored locally with `delivery_status=queued_no_webhook`.
- Notification records and payloads must not expose webhook URLs, HubSpot tokens, or secrets.

Phase 7 checks:

```bash
cd apps/api
python scripts/test_demo_story_runner.py
python scripts/test_failure_notifications.py
```

## Dashboard Demo History Seed

For interview demos, use two data paths:

1. Run one real proof journey with HubSpot enabled:

```bash
cd apps/api
python scripts/run_full_demo_story.py --reset-demo
```

2. Seed local synthetic dashboard history without calling HubSpot:

```bash
python scripts/seed_dashboard_demo_data.py --count 40
```

The full demo story can prove the real CRM adapter path. The dashboard seed forces mock/local CRM mode and creates synthetic persisted history for the Sales Manager Dashboard and Admin Dashboard, including leads, safe CRM updates, review items, approvals, rejections, workflow steps, audit events, notifications, partial/failed mock sync examples, and operational diagnostics.

HubSpot remains the CRM source of truth for the real proof record. Bulk dashboard history is local synthetic data only; production would use real CRM and workflow history instead of seed data.

Optional local reset:

```bash
python scripts/seed_dashboard_demo_data.py --reset-demo --count 40
```

Seed verification:

```bash
python scripts/test_dashboard_demo_seed.py
python scripts/test_sales_manager_dashboard_metrics.py
python scripts/test_admin_dashboard_metrics.py
```

## Phase 4: Mock CRM Adapter and CRM Records

Lead Intake now writes CRM-style records through a local mock CRM adapter. The adapter keeps the system local and deterministic while preparing a clean boundary for a future HubSpot adapter.

Backend routes:

```text
GET /crm/leads
GET /crm/leads/{crm_record_id}
GET /crm/leads/{crm_record_id}/activities
```

Frontend page:

```text
http://localhost:3000/crm-records
```

Run the adapter check from `apps/api`:

```bash
python scripts/test_mock_crm_adapter.py
```

Mock mode remains the default and does not call external APIs.

## Phase 5: Optional HubSpot Sandbox Adapter

The CRM adapter now supports two modes:

- `mock`: local-only default.
- `hubspot`: optional sandbox write-back through a HubSpot private app token.

Environment variables:

```bash
CRM_ADAPTER_MODE=mock
HUBSPOT_ENABLED=false
HUBSPOT_ACCESS_TOKEN=
HUBSPOT_PORTAL_ID=
HUBSPOT_DEFAULT_PIPELINE=
HUBSPOT_DEFAULT_DEAL_STAGE=
HUBSPOT_OWNER_ID=
```

Backend routes:

```text
GET /hubspot/status
POST /hubspot/setup-properties
POST /hubspot/sync/lead/{lead_id}
```

Frontend pages:

```text
http://localhost:3000/crm-records
http://localhost:3000/hubspot-status
```

Supported AI property names:

```text
ai_lead_score
ai_priority
ai_route
ai_confidence
ai_next_action
ai_human_review_required
ai_last_workflow_run
ai_hygiene_score
ai_risk_level
ai_follow_up_status
ai_proposal_status
```

Set up properties intentionally from `apps/api`:

```bash
python scripts/setup_hubspot_properties.py
```

Run no-network HubSpot adapter checks:

```bash
python scripts/test_hubspot_adapter_config.py
python scripts/test_hubspot_adapter_mapping.py
```

Optional manual sandbox smoke test:

```bash
python scripts/smoke_test_hubspot_sandbox.py
```

The smoke test only runs when HubSpot mode is explicitly enabled and a token is configured. It uses synthetic demo data only.

Latest verified smoke result:

```text
crm_update_status=applied
hubspot_sync_status=synced
review_created=False
risk_flags=[]
hubspot_contact_id returned
hubspot_company_id returned
hubspot_deal_id returned
hubspot_task_id returned
hubspot_note_id returned
audit_events=16
workflow_step_events=23
guardrail_audit_events=0
```

HubSpot hardening:

- Local/mock tests force mock mode even when `.env` is configured for HubSpot.
- HubSpot mapping tests do not perform network calls.
- Only `scripts/smoke_test_hubspot_sandbox.py` intentionally writes to HubSpot.
- Standard HubSpot company fields are normalized before sync.
- Task payloads include required HubSpot task fields.
- Optional activity failures preserve core contact, company, and deal sync.
- Tokens are never returned or logged.

## Phase 6: Sales Manager and Admin Dashboards

Phase 6 adds two distinct dashboard layers:

- Sales Manager Dashboard: business-facing sales execution, AI adoption, drop-off zones, pipeline health, and estimated time saved.
- Admin / Operations Dashboard: review queue health, audit health, workflow health, operational failures, HubSpot sync health, and recommended fixes.

Frontend pages:

```text
http://localhost:3000/dashboard
http://localhost:3000/admin-dashboard
```

Backend routes:

```text
GET /metrics/sales-manager-dashboard
GET /metrics/admin-dashboard
```

Dashboard metrics use persisted backend data. If a metric cannot be calculated from the current data model, the API returns a clear `not_enough_data` state instead of inventing numbers.

## Acceptance Criteria

Every workflow, adapter, automation, and integration must include:

- Business audit trail.
- Operational observability.
- Passing tests.
- Clean failure diagnostics.
- Explicit human-review policy where relevant.
- Documentation updates when routes, workflows, entities, or the demo story change.

### Web

```bash
cd apps/web
npm install
npm run dev
```

Dashboard:

```text
http://localhost:3000
```

## Safety Notes

- Use `.env.example` as a template only.
- Do not commit real API keys.
- External APIs are not called in default mock mode.
- HubSpot sandbox calls require explicit `CRM_ADAPTER_MODE=hubspot`, `HUBSPOT_ENABLED=true`, and a private app token.
- Human review is expected before any future AI-generated output is sent to customers or written to CRM systems.
