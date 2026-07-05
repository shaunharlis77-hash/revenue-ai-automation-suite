# n8n Workflow Exports

These JSON files are importable n8n workflow drafts for the Revenue AI Automation Suite demo.

n8n is the orchestration layer. It receives webhooks, runs scheduled triggers, and calls the FastAPI backend. It does not hold the core scoring, summarization, routing, review, CRM writeback, audit, or guardrail logic.

## Architecture Role

- FastAPI remains the business logic and AI decisioning layer.
- HubSpot or the mock CRM adapter remains the CRM source of truth.
- n8n orchestrates external events, scheduled checks, and failure notifications.
- Audit events and operational step events are still written by the backend.
- No credentials or secrets are included in these workflow files.

## API Base URL

Set this environment variable in n8n:

```text
API_BASE_URL=http://host.docker.internal:8000
```

Use that value when n8n runs in Docker on the same machine as the FastAPI backend.

## Workflows

- `lead-intake-to-api.json`: Webhook receives lead form data and calls `POST /intake/lead`.
- `meeting-completed-to-summary.json`: Webhook receives meeting notes plus `crm_record_id` and calls `POST /demo/records/{crm_record_id}/meeting`.
- `review-approved-crm-writeback.json`: Webhook receives a review approval and calls the backend review approval route. The backend decides whether CRM writeback is allowed.
- `weekly-crm-hygiene.json`: Schedule trigger calls the backend demo path for local weekly hygiene/demo orchestration. Production hygiene should still call backend-owned hygiene endpoints.
- `workflow-failure-notification.json`: Webhook receives safe failure notifications from the backend. It returns a no-op response unless you add Slack/email credentials.
- `full-demo-story-orchestrator.json`: Manual or webhook trigger calls `POST /demo/full-story/run` for interview demo setup.

## Import Steps

1. Open n8n.
2. Choose **Import from File**.
3. Select one of the JSON files in this folder.
4. Set `API_BASE_URL` in the n8n environment.
5. Keep workflows inactive until the FastAPI backend is running.
6. Add Slack/email credentials only in n8n if you want external notification delivery.

These workflows are intentionally simple so the interview demo can show that n8n coordinates events while the backend remains the controlled system of record for decisions, guardrails, audit trail, and operational observability.
