# Operational Guardrails

## Purpose

This project is not only about making workflows run. It is also about making them safe, observable, and maintainable.

Every workflow should be easy to understand, easy to monitor, and safe to stop or review when something looks wrong.

## Observability

Every workflow should make it clear:

- Whether it ran.
- Whether it succeeded or failed.
- Where it failed.
- Why it failed.
- What should happen next.

Future workflow tracking should include:

- `workflow_run_id`
- `workflow_name`
- `status`
- `started_at`
- `completed_at`
- `failed_at`
- `failure_step`
- `failure_reason`
- `retry_recommended`
- `human_review_required`

The goal is to let a sales or operations teammate understand the workflow state without reading code.

## Data Integrity

The CRM should remain the source of truth.

Rules:

- Validate inputs before processing.
- Do not overwrite trusted CRM data with low-confidence AI output.
- Separate AI suggestions from approved CRM updates.
- Risky changes require human review.
- Log every suggested or completed update.

Future CRM updates should be controlled, reviewable, and reversible where possible.

## Security

Security should stay simple and strict:

- No secrets in code.
- Use environment variables.
- Use least-privilege API tokens later.
- Do not log unnecessary sensitive data.
- Use summaries in logs where possible.
- Keep external integrations controlled.

The foundation does not include real API keys or live external integrations.

## Authentication and Access Control

The dashboard will eventually need user roles.

Simple future roles:

- `sales_rep`
- `sales_manager`
- `admin`

Expected access pattern:

- Reps review their own items.
- Managers see workflow metrics and pipeline health.
- Admins manage integrations and workflow settings.

Access control should be added before real CRM data or customer-facing workflows are connected.

## Human Review

Human review should be required before:

- Customer-facing messages.
- Proposal drafts.
- CRM ownership changes.
- Deal stage changes.
- Low-confidence outputs.
- Enterprise or high-risk leads.
- Disqualified, test, or spam-like leads are deleted or suppressed.

The system should make it clear what is suggested, what is approved, and who approved it.

## Failure Handling

Failures should not silently break the sales process.

If a workflow fails:

- Leave CRM unchanged.
- Create a review item if needed.
- Log the failed step and reason.
- Allow the rep to continue manually.

The safest fallback is a clear handoff to a human, not an invisible partial update.

## How This Supports the Role

These guardrails map to operating responsibly, documenting workflows, keeping CRM data reliable, and making automations maintainable by someone other than the builder.

They also show that the project is designed for real sales operations use, where trust, visibility, and handoffs matter as much as automation speed.

