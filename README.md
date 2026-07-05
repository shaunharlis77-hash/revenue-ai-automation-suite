# revenue-ai-automation-suite

Foundation for a revenue AI automation suite that will eventually support sales operations workflows across a web dashboard, FastAPI backend, n8n automations, HubSpot, and AI-assisted task flows.

This repository is intentionally simple at this stage. It does not include real AI workflows, HubSpot integration, external API calls, authentication, or production secrets.

## What This Project Is

The project is a working foundation for an internal sales operations automation system. The long-term goal is to help revenue teams reduce manual work across lead scoring, meeting summaries, follow-up drafting, CRM hygiene, proposal drafting, knowledge retrieval, impact reporting, and human review.

## Current Status

- Foundation verified locally.
- API placeholder routes available.
- Dashboard shell running.
- Next step is Workflow 1: Lead Scoring and Routing.

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
GET  /metrics/dashboard
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

No real HubSpot, n8n, LangGraph, external API, email, auth, Docker, or Postgres integration is included.

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
- No external APIs are called in this foundation.
- Human review is expected before any future AI-generated output is sent to customers or written to CRM systems.
