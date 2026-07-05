# Build Log

## 2026-07-05

### Phase 7: Full Demo Story and n8n Orchestration

Completed the end-to-end interview demo story and added n8n orchestration exports.

Implemented:

- Full demo story runner that follows one synthetic lead from first touch through pipeline management.
- Meeting/call CRM attachment through `POST /demo/records/{crm_record_id}/meeting`.
- Meeting summary CRM writeback using the existing deterministic meeting summary workflow.
- Follow-up approval writeback through the existing review approval route when review items include CRM context.
- Follow-up outcome capture through `POST /demo/records/{crm_record_id}/follow-up-outcome`.
- Proposal/package outline approval writeback and proposal status activity in the demo story runner.
- CRM hygiene demo run that creates review visibility for risky records.
- Failure notification layer that queues locally when `N8N_FAILURE_WEBHOOK_URL` is not configured and posts safe payloads when it is configured.
- Review notification layer for review-required items, including assigned-owner routing and manager fallback when no owner is available.
- Notification routes at `GET /notifications`, `GET /notifications/recent`, and `POST /notifications/test-failure`.
- Importable n8n JSON workflows for lead intake, meeting completion, review approval writeback, weekly hygiene/demo orchestration, workflow failure notification, and full demo story orchestration.
- Dashboard-ready data seeding through persisted CRM records, CRM activities, audit events, review items, workflow runs, workflow step events, and notification events.
- Added `scripts/test_demo_story_runner.py` and `scripts/test_failure_notifications.py`.

Guardrails preserved:

- FastAPI remains the business logic and AI decisioning layer.
- HubSpot/mock CRM remains the CRM source of truth.
- n8n orchestrates events and schedules but does not hold core workflow logic.
- Audit trail and operational observability remain mandatory.
- Notification payloads exclude secrets and tokens.
- Review notifications write audit events and workflow step events.
- Manager fallback notifications write explicit fallback audit metadata.
- No Postgres migration, authentication, LangGraph, n8n business logic, or customer-facing auto-send behavior was added.

### Phase 7: Dashboard Demo History Seed

Added a lightweight local dashboard history seed for interview presentation.

Implemented:

- `scripts/seed_dashboard_demo_data.py` for 30-40 synthetic local CRM/demo records.
- Forced mock/local CRM mode inside the bulk seed path so HubSpot is not called even when `.env` is configured for HubSpot.
- Varied synthetic lead/deal journeys across high, medium, low, and blocked/risky cases.
- Persisted CRM records, workflow runs, audit events, workflow step events, review items, review decisions, notifications, and CRM activity history.
- Review-required examples with assigned owner/routed rep notifications and manager fallback notifications.
- Follow-up drafts, proposal outlines, CRM hygiene risk findings, approved reviews, rejected reviews, partial/failed mock sync metadata, missing next-step examples, and a controlled operational failure notification.
- `scripts/test_dashboard_demo_seed.py` to verify seeded persistence, dashboard metrics, mock mode, notifications, and secret-safe output.

Demo setup:

- Run one real proof journey with HubSpot enabled through `python scripts/run_full_demo_story.py --reset-demo`.
- Then seed local synthetic dashboard history with `python scripts/seed_dashboard_demo_data.py --count 40`.
- HubSpot remains the CRM source of truth for the real proof record.
- Bulk dashboard history is local synthetic data only; production would use real CRM and workflow history.

No real HubSpot records, secrets, external API calls, frontend-only fake metrics, or dashboard contract changes were added.

### Phase 6B: Suite-Wide UI Polish Pass

Polished the frontend suite so the dashboards, workflow pages, CRM pages, governance pages, and operational pages feel like one coherent Revenue AI / Sales AI Ops product.

Included:

- Updated the global visual system with calmer SaaS spacing, typography, cards, badges, tables, forms, loading states, empty states, and error states.
- Added active sidebar navigation while preserving grouped navigation for Dashboards, Workflows, CRM, Governance, and Operations.
- Added reusable UI primitives for sidebar navigation, detail cards, and loading states.
- Improved page headers and placeholder workflow pages so they explain current behavior, guardrails, and review boundaries in plain language.
- Polished Sales Manager Dashboard metric emphasis and Admin Dashboard operational risk emphasis.
- Improved Review Queue, Audit Trail, Operational Logs, CRM Records, Lead Intake, HubSpot Status, Impact Metrics, and Sales Knowledge Base demo readability.
- Updated visible Lead Intake demo defaults to valid-looking synthetic business domains.
- Preserved the product distinction between Review Queue, Audit Trail, Operational Logs, and CRM/HubSpot source-of-truth views.

No backend workflow logic, API response contracts, HubSpot guardrails, n8n integration, LangGraph integration, secrets, or audit/observability requirements were changed.

### Phase 6: Sales Manager and Admin Dashboards

Implemented two dashboard layers with a controlled frontend polish pass.

Implemented:

- Sales Manager Dashboard added.
- Admin / Operations Dashboard added.
- Sales manager metrics API added at `GET /metrics/sales-manager-dashboard`.
- Admin metrics API added at `GET /metrics/admin-dashboard`.
- Sales performance and pipeline health summaries.
- Drop-off zone stats.
- Team AI adoption and usage metrics.
- Rep-level AI usage reporting where attribution data exists, with `not_enough_rep_level_data` returned when attribution is unavailable.
- AI impact and estimated time saved.
- Sales execution risk visibility.
- CRM and HubSpot sync visibility.
- Guardrail visibility.
- Operational health visibility.
- Frontend UI polish pass with grouped navigation, clearer dashboard hierarchy, reusable dashboard UI components, readable tables, and improved empty/error states.
- Audit and observability layers remain mandatory acceptance criteria.

Metric policy:

- Metrics use persisted backend data from workflow runs, audit events, review items, workflow step events, CRM records, and CRM activities.
- Metrics that cannot be calculated from current persisted data return `not_enough_data` instead of invented values.
- Time saved is labeled as estimated.
- No tokens or secrets are returned.

Added tests:

- `scripts/test_sales_manager_dashboard_metrics.py`.
- `scripts/test_admin_dashboard_metrics.py`.

No workflow logic, HubSpot guardrails, mock mode behavior, n8n automation, LangGraph integration, auth, or secret handling was weakened.

### Phase 5: HubSpot Sandbox Integration verified

Completed the Phase 5 HubSpot sandbox integration lock.

Implemented:

- HubSpot CRM adapter behind the CRM adapter boundary.
- Mock adapter remains default and safe.
- HubSpot mode controlled by environment variables.
- HubSpot status endpoint.
- HubSpot property setup script.
- Contact sync.
- Company sync.
- Deal sync.
- Task creation.
- Note creation.
- AI custom property sync.
- HubSpot-safe company property normalization.
- HubSpot-safe task payload mapping.
- Optional external activity failure handling.
- Real sandbox smoke test.
- Token-safe responses.

Verification completed:

- HubSpot property setup completed successfully.
- `test_hubspot_adapter_mapping.py` passed.
- `test_hubspot_adapter_config.py` passed.
- `test_mock_crm_adapter.py` passed in forced mock mode.
- `test_lead_intake.py` passed in forced mock mode.
- Real HubSpot smoke test passed.

Smoke test result:

- `crm_update_status=applied`.
- `hubspot_sync_status=synced`.
- `review_created=False`.
- `risk_flags=[]`.
- HubSpot contact ID returned.
- HubSpot company ID returned.
- HubSpot deal ID returned.
- HubSpot task ID returned.
- HubSpot note ID returned.
- `audit_events=16`.
- `workflow_step_events=23`.
- `guardrail_audit_events=0`.

Key hardening:

- Local/mock tests force mock mode even when `.env` is configured for HubSpot.
- HubSpot mapping tests do not perform network calls.
- Only `smoke_test_hubspot_sandbox.py` intentionally writes to HubSpot.
- HubSpot standard fields are normalized before sync.
- Industry values are mapped to HubSpot-safe enum values.
- `numberofemployees` is mapped to an integer.
- Task payload includes required HubSpot task fields.
- Optional activity failures preserve core contact, company, and deal sync.
- Tokens are never returned or logged.

No real tokens or secret values were added to documentation or committed files.

### Phase 5: HubSpot Sandbox Integration

Added an optional HubSpot sandbox adapter behind the existing CRM adapter boundary.

Included:

- Added HubSpot environment settings with safe mock-mode defaults.
- Added a CRM adapter factory that selects mock mode unless HubSpot mode is explicitly enabled.
- Added `hubspot_adapter.py` with contact, company, deal, task, note, association, sync status, and custom property setup support.
- Added HubSpot object mapping for Lead Intake outputs and AI custom properties.
- Added HubSpot sync metadata to local CRM lead records so the CRM Records UI remains useful in both modes.
- Added HubSpot audit events for sync started, object upserts, task/note creation, associations, sync completion, sync failure, and blocked sync.
- Added HubSpot operational step events for sync start, object creation/update, property checks, associations, completion, skipped sync, and failure diagnostics.
- Added `/hubspot/status`, `/hubspot/setup-properties`, and `/hubspot/sync/lead/{lead_id}`.
- Added `scripts/setup_hubspot_properties.py`.
- Added `scripts/test_hubspot_adapter_config.py` and `scripts/test_hubspot_adapter_mapping.py`.
- Added optional manual `scripts/smoke_test_hubspot_sandbox.py` for intentional sandbox testing only.
- Updated CRM Records and Lead Intake UI to show adapter mode, HubSpot sync status, HubSpot IDs, last sync time, and sync errors.
- Added `/hubspot-status`.

Policy preserved:

- Mock mode remains the default and does not call HubSpot.
- Safe clean lead updates can sync automatically when HubSpot mode is explicitly enabled.
- High-priority leads can sync with review visibility.
- Risky or ambiguous leads block sensitive HubSpot sync pending review.
- Customer-facing emails, follow-ups, and proposals are never sent automatically.
- HubSpot private app tokens are read only from environment variables and are never returned in API responses.

Frontend verification: `npm run build` passed.

Python test execution was not available in the current shell because no Python launcher was found. Added no-network test scripts for local verification.

No n8n, LangGraph, external enrichment API, email sending, auth, Docker/Postgres change, or real customer data was added.

### Phase 4: Mock CRM Adapter and CRM Records View

Added a local mock CRM adapter foundation and CRM Records admin view.

Included:

- Added a mock CRM adapter service around the internal CRM-style lead record persistence.
- Routed Lead Intake CRM writes through the adapter while preserving the existing safe-update policy.
- Added persistent CRM activity records for lead creation, enrichment, scoring, route assignment, applied updates, blocked updates, and review visibility.
- Added `/crm/leads`, `/crm/leads/{crm_record_id}`, and `/crm/leads/{crm_record_id}/activities`.
- Added adapter audit events for write started, write applied, write blocked, activity created, and write failed.
- Added adapter workflow step events for write started, record loaded, record created or updated, activity created, write completed, and write failed.
- Added `scripts/test_mock_crm_adapter.py`.
- Added `/crm-records` frontend page and sidebar navigation.
- Linked Lead Intake results to the matching CRM record.

Policy preserved:

- Clean leads apply safe CRM-style updates automatically.
- High-priority leads apply safe updates immediately with review visibility.
- Risky, suspicious, ambiguous, or low-confidence leads block sensitive updates pending review.

No real HubSpot, n8n, LangGraph, external APIs, email sending, auth, Docker/Postgres change, or real customer data was added.

### Phase 3 lead intake CRM decision policy fix

Fixed the Lead Intake CRM update decision logic before locking Phase 3.

Included:

- Separated blocking review reasons from review-visibility reasons.
- Ensured high-priority leads are not blocked just because review visibility is useful.
- Preserved automatic safe CRM-style updates for clean leads.
- Preserved `blocked_pending_review` for suspicious, low-confidence, disqualified, or ambiguous leads.
- Removed accidental suspicious wording from clean and high-priority test inputs.
- Improved lead intake test failure messages with CRM status, priority, confidence, enrichment confidence, risk flags, review status, and review reasons.

Cause:

- Service decision logic needed a clearer separation between blocking review and review visibility.
- Clean and high-priority test notes contained the word `test`, which correctly triggered the suspicious/test-submission guardrail.

Frontend verification: `npm run build` passed.

Python test execution was not available in the current shell because no Python launcher was found.

### Phase 3 lead intake verification cleanup

Tightened the Phase 3 lead intake verification pass.

Included:

- Updated `scripts/test_lead_intake.py` with explicit assertion messages for CRM update status, review item creation, audit events, and workflow step events.
- Updated the test to use unique test emails and workflow-run-scoped audit/review/step queries so it does not depend on a globally empty database.
- Relaxed the clean lead test to assert the automation policy instead of an exact priority label.
- Updated the Lead Intake result panel to show `CRM update status` and `Review created` as explicit fields, not only badges.

Frontend verification: `npm run build` passed.

Python test execution was not available in the current shell because no Python launcher was found.

### Phase 3: Lead Intake and Enrichment

Added the first end-to-end lead intake flow: "A lead comes in."

Included:

- Added `POST /intake/lead`.
- Added `GET /intake/leads` and `GET /intake/leads/{lead_id}`.
- Added deterministic/mock lead enrichment with persona, company size band, normalized industry/region, likely team, CRM match status, fit notes, confidence, buying signals, and risk flags.
- Added a local `crm_lead_records` persistence table for safe internal CRM-style write-back.
- Added orchestration for input validation, enrichment, scoring, routing decision, CRM-style record update, review item creation when needed, audit events, workflow logs, and workflow step events.
- Added CRM update statuses: `applied`, `applied_with_review_visibility`, and `blocked_pending_review`.
- Added audit events for lead receipt, enrichment, scoring, route recommendation, CRM update applied/blocked, guardrails, review creation, and workflow completion.
- Added workflow step events for the full intake path and failure diagnostics.
- Added `/lead-intake` frontend page with form submission, demo presets, result panel, and links to Review Queue, Audit Trail, and Operational Logs.
- Added `scripts/test_lead_intake.py`.

Policy captured:

- Clean leads can be enriched, scored, routed, and written to the internal CRM-style record automatically.
- High-priority leads can be written automatically while also creating review visibility.
- Risky, suspicious, low-confidence, or ambiguous leads block sensitive CRM routing/status actions pending review.
- Customer-facing actions are still not sent automatically.

Verified frontend with `npm run build`.

Python test execution was not available in the current shell because no Python launcher was found.

No real HubSpot, n8n, LangGraph, external enrichment API, email sending, auth, Docker/Postgres change, real customer data, or backend guardrail weakening was added.

### Phase 2: Admin Operational Observability UI

Added an Operational Logs admin screen for step-level workflow maintenance and failure diagnosis.

Included:

- Added `/operational-logs`.
- Added Operational Logs to the sidebar navigation.
- Added frontend API support for `GET /logs/workflow-steps`.
- Added summary cards for total step events, failed steps, warning/skipped steps, critical/error severity steps, retryable failures, and unique workflow runs.
- Added a failure diagnostics section that shows where a workflow failed, why it failed, whether it is retryable, and what a maintainer should check.
- Added a reverse-chronological step event list with badges for status, severity, and retryable failures.
- Added a simple workflow name or workflow run id filter.
- Added loading, empty, and backend-unavailable states.

The admin UI now has three clear views:

- Review Queue: human decision layer.
- Audit Trail: business/governance traceability.
- Operational Logs: step-level maintenance and failure diagnosis.

Verified with `npm run build`.

No backend workflow logic, HubSpot integration, n8n automation, LangGraph, Postgres, Docker, auth, or guardrail changes were added.

## 2026-07-03

### Demo seed journey added

Added a local demo seed script so the Review Queue and Audit Trail UI have realistic data to display.

Included:

- Added `apps/api/scripts/seed_demo_journey.py`.
- Seed script calls existing workflow services instead of hardcoding only database rows.
- Demo journey covers Northstar Analytics and Maya Chen across lead scoring, meeting summary, follow-up drafting, proposal/package outline drafting, and CRM hygiene.
- Demo data creates review items, audit events, workflow runs, and workflow step events.
- Demo includes pending, approved, and rejected review items.
- Review approval and rejection create audit events and operational step events.
- Demo guardrails include customer-facing review, no auto-send, pricing/budget review, and high-risk deal review signals.
- Demo includes a safe simulated failure diagnostic with `recommended_fix` populated.
- Default seed behavior is append-only. A `--reset-local-demo` flag exists for explicit local demo resets.

No HubSpot, n8n, LangGraph, frontend changes, LLM/API calls, external integrations, or real customer data were added.

### Operational observability backfill

Added persistent step-level operational observability across the existing backend system.

Included:

- Added a `workflow_step_events` persistence table for maintenance and failure diagnosis.
- Added a workflow step event model and service with `log_step_started`, `log_step_success`, `log_step_failure`, `log_step_skipped`, step listing, and workflow-run lookup.
- Added `GET /logs/workflow-steps` and `GET /logs/workflow-steps/{workflow_run_id}`.
- Backfilled step events across Lead Scoring and Routing, Meeting Capture and CRM Summary, Follow-Up Drafting, Proposal / Package Outline Drafting, and CRM Hygiene / Deal Risk Monitor.
- Added operational step events for review approval and rejection decisions.
- Added failure-step logging with error type, error message, failure reason, retryable flag, and recommended fix.
- Preserved workflow run logs, persistent audit events, and persistent review items.
- Added `scripts/test_workflow_step_events.py`.
- Added `scripts/test_workflow_failure_observability.py`.

This separates governance history from maintenance diagnostics: `audit_events` explain what happened and who decided; `workflow_step_events` explain which operational step ran, failed, or needs attention.

No workflow business logic, HubSpot integration, n8n automation, LangGraph, frontend changes, LLM/API calls, auth, or CRM write-back was added.

### Phase 2: Review Queue UI and Audit Trail Screen

Added the first visible product layer for workflow review and audit visibility.

Included:

- Added Review Queue navigation.
- Added Audit Trail navigation.
- Added `NEXT_PUBLIC_API_BASE_URL` frontend configuration with local API fallback.
- Added a Review Queue screen that lists persistent review items, shows review context, and supports approve/reject actions.
- Added an Audit Trail screen that lists durable audit events in reverse chronological order.
- Added loading, empty, and backend-unavailable states.
- Added visual emphasis for pending, approved, rejected, high/critical risk, customer-facing review, CRM update review, guardrail, review, failure, and CRM update events.

No backend workflow logic, HubSpot integration, n8n automation, LangGraph, full executive dashboard, or frontend authentication was added.

### Phase 1B: Workflow Audit and Review Queue Integration verified

Implemented persistent audit/review integration across existing workflows.

Included:

- Lead scoring now creates durable audit events.
- Meeting summary now creates durable audit events.
- Follow-up drafting now creates a persistent review item and audit events.
- Proposal/package outline drafting now creates a persistent review item and audit events.
- CRM hygiene now creates persistent review items and audit events for risky deals.
- Guardrail-triggered audit events are captured for workflows requiring human review.
- Review approvals and rejections continue to create audit events.
- Existing workflow logs remain working.

Verified with:

- `python scripts/test_workflow_audit_integration.py`
- `python scripts/test_audit_trail.py`
- `python scripts/test_review_queue.py`
- `python scripts/test_workflow_logs.py`

Results:

- Workflow audit integration: 6 passed, 0 failed.
- Audit trail foundation: 3 passed, 0 failed.
- Review queue foundation: 3 passed, 0 failed.
- Workflow logs: 2 passed, 0 failed.

Full checkpoint:

- `python scripts/test_lead_scoring.py` -> 8 passed, 0 failed.
- `python scripts/test_meeting_summary.py` -> 6 passed, 0 failed.
- `python scripts/test_workflow_logs.py` -> 2 passed, 0 failed.
- `python scripts/test_follow_up.py` -> 6 passed, 0 failed.
- `python scripts/test_proposal.py` -> 6 passed, 0 failed.
- `python scripts/test_crm_hygiene.py` -> 7 passed, 0 failed.
- `python scripts/test_audit_trail.py` -> 3 passed, 0 failed.
- `python scripts/test_review_queue.py` -> 3 passed, 0 failed.
- `python scripts/test_workflow_audit_integration.py` -> 6 passed, 0 failed.

Total: 47 passed, 0 failed.

### Phase 1B: Workflow Audit and Review Queue Integration

Wired the existing deterministic workflows into the persistent audit trail and review queue.

Included:

- Added workflow-specific audit events for lead scoring, meeting summaries, follow-up drafts, proposal outlines, and CRM hygiene checks.
- Added durable `workflow_started`, workflow-specific, guardrail, review, CRM recommendation, and `workflow_completed` events.
- Added persistent review item creation for customer-facing drafts, proposal outlines, meeting review actions, high-risk CRM hygiene cases, and human-review-required lead scoring outputs.
- Preserved the existing in-memory workflow logging while adding durable audit and review records.
- Added `scripts/test_workflow_audit_integration.py`.

No workflow logic was rewritten, and no HubSpot, n8n, frontend, LangGraph, LLM/API calls, auth, or CRM write-back was added.

### Phase 1: Persistence, Audit Trail, and Review Queue Foundation

Added the local persistence foundation for workflow operations.

Included:

- Added `DATABASE_URL` configuration with SQLite fallback for local development and demos.
- Added database table creation for `workflow_runs`, `audit_events`, and `review_items`.
- Preserved the existing in-memory workflow log interface while persisting workflow runs to the database.
- Added append-only audit trail service and routes for listing and retrieving audit events.
- Added persistent review queue service and routes for listing, retrieving, approving, and rejecting review items.
- Added audit events for review item creation, approval, and rejection.
- Added decision and decision reason persistence for approved and rejected review items.
- Added `scripts/test_audit_trail.py`.
- Added `scripts/test_review_queue.py`.

No HubSpot integration, n8n automation, LangGraph, LLM/API calls, frontend work, auth, or CRM write-back was added.

### Workflow 5: CRM Hygiene / Deal Risk Monitor verified

Verified Workflow 5 locally.

Included:

- Implemented deterministic CRM hygiene scoring and deal risk monitoring.
- Added sample CRM hygiene inputs and expected results.
- Added detection for missing owner, missing next step, stale activity, missing high-priority follow-up, pending proposal review, long stage age, missing CRM fields, and open risks.
- Added hygiene score from 0 to 100.
- Added risk levels: low, medium, high, critical.
- Added read-only guardrails so CRM records are not mutated automatically.
- Added recommended actions, human-review flagging, next action, confidence, and reasoning.
- Wired Workflow 5 into the observability log service.
- Verified with `python scripts/test_crm_hygiene.py`.
- Result: 7 passed, 0 failed.

Full backend checkpoint passed:

- `python scripts/test_lead_scoring.py` -> 8 passed, 0 failed.
- `python scripts/test_meeting_summary.py` -> 6 passed, 0 failed.
- `python scripts/test_workflow_logs.py` -> 2 passed, 0 failed.
- `python scripts/test_follow_up.py` -> 6 passed, 0 failed.
- `python scripts/test_proposal.py` -> 6 passed, 0 failed.
- `python scripts/test_crm_hygiene.py` -> 7 passed, 0 failed.

### Workflow 5: CRM Hygiene / Deal Risk Monitor implemented

Implemented the deterministic foundation for Workflow 5.

Included:

- Added Pydantic request and response models for CRM hygiene checks.
- Added deterministic CRM hygiene and deal risk monitoring service.
- Wired `POST /ai/check-crm-hygiene` to the service.
- Added 6 synthetic CRM hygiene cases and expected results.
- Added hygiene score, risk level, issues, missing fields, stale activity, recommended actions, human review flag, next action, confidence, and reasoning.
- Added read-only guardrails: CRM records are not mutated automatically.
- Added rules for missing owners, missing next steps, stale activity, high-priority follow-up gaps, pending proposal review, long stage age, missing CRM fields, and open risks.
- Wired Workflow 5 into the local workflow run logging service.
- Added `scripts/test_crm_hygiene.py`.

No HubSpot integration, n8n automation, LLM/API calls, database, auth, or CRM write-back was added.

### Workflow 4: Proposal / Package Outline Drafting verified

Verified Workflow 4 locally.

Included:

- Implemented deterministic internal proposal/package outline drafting.
- Added sample proposal inputs and expected results.
- Added proposal title, executive summary, problem statement, recommended package, scope items, implementation considerations, assumptions, exclusions, risk notes, review reasons, confidence, next action, and reasoning.
- Added mandatory human review for all proposal outlines.
- Added guardrails for pricing, budget, security, legal, implementation, adoption, urgent timeline, and missing-context cases.
- Added banned-promise-language checks so proposal outlines do not include guarantees, legal/security claims, fixed-price claims, or final/binding proposal language.
- Wired Workflow 4 into the observability log service.
- Verified with `python scripts/test_proposal.py`.
- Result: 6 passed, 0 failed.

### Workflow 4: Proposal / Package Outline Drafting implemented

Implemented the deterministic foundation for Workflow 4.

Included:

- Added Pydantic request and response models for proposal outline drafting.
- Added deterministic proposal/package outline drafting service.
- Wired `POST /ai/draft-proposal` to the service.
- Added 5 synthetic proposal cases and expected results.
- Added internal-outline guardrails: outlines are not final proposals and always require human review.
- Added review reasons and risk notes for pricing, budget, security, legal, implementation, adoption, urgent timeline, and missing-context cases.
- Added banned promise language checks for unsafe proposal claims.
- Wired Workflow 4 into the local workflow run logging service.
- Added `scripts/test_proposal.py`.

No HubSpot integration, n8n automation, LLM/API calls, database, auth, proposal sending, or email/message sending was added.

### Workflow 3: Follow-Up Drafting verified

Verified Workflow 3 locally.

Included:

- Implemented deterministic follow-up drafting workflow.
- Added sample follow-up input dataset and expected results.
- Added customer-facing draft generation with mandatory human review.
- Added review reasons and risk notes for pricing, security, implementation, adoption, and missing-next-step cases.
- Added banned-promise-language checks so drafts do not include unsafe claims such as guarantees, legal approval, full security, or definite implementation promises.
- Wired Workflow 3 into the observability log service.
- Verified with `python scripts/test_follow_up.py`.
- Result: 6 passed, 0 failed.

### Workflow 3: Follow-Up Drafting implemented

Implemented the deterministic foundation for Workflow 3.

Included:

- Added Pydantic request and response models for follow-up drafting.
- Added deterministic follow-up drafting service.
- Wired `POST /ai/draft-follow-up` to the service.
- Added 5 synthetic follow-up cases and expected results.
- Added customer-facing guardrails: drafts are never sent automatically and always require human review.
- Added review reasons and risk notes for pricing, security, implementation, adoption, and missing-next-step cases.
- Added banned promise language checks.
- Wired Workflow 3 into the local workflow run logging service.
- Added `scripts/test_follow_up.py`.

No HubSpot integration, n8n automation, LLM/API calls, database, auth, or message sending was added.

### Observability and guardrails foundation added

Added a simple local observability foundation for completed workflows.

Included:

- Added shared Pydantic workflow run log and metrics models.
- Added an in-memory workflow log service for start, success, failure, recent runs, and metrics.
- Updated `/logs` endpoints for workflow run visibility.
- Updated `/metrics/dashboard` to return workflow run metrics.
- Wired Workflow 1 and Workflow 2 into local workflow run logging.
- Added output summaries, human-review visibility, input references, and next actions to workflow logs.
- Added `scripts/test_workflow_logs.py` for local observability checks.

No database, HubSpot integration, n8n automation, LLM calls, auth, or external API calls were added.

### Workflow 2: Meeting Capture and CRM Summary

Verified Workflow 2 locally.

Included:

- Implemented deterministic meeting-summary workflow.
- Added sample meeting transcript dataset and expected results.
- Added CRM-ready note generation, pain point detection, objection detection, buying-signal detection, next-step extraction, follow-up due detection, deal-stage recommendation, proposal flagging, confidence rating, needs-more-info flag, human-review flag, and recommended actions.
- Added distinction between auto-allowed internal actions and review-required customer/deal actions.
- Fixed action-description cleanup by keeping wording cleanup in the service layer and removing model-level mutation.
- Verified with `python scripts/test_meeting_summary.py`.
- Result: 6 passed, 0 failed.
- Added strict recommended-action description validation to the meeting summary test.
- The test now checks for dirty joined-word fragments such as "thereview", "Createa", "nextsteps", "aretoo", "actionsto", and "withrevenue".
- Verified actual service string output using `repr()` to avoid terminal wrapping/copy artifacts.
- Confirmed all recommended action descriptions are clean.
- Result: `python scripts/test_meeting_summary.py` returns 6 passed, 0 failed.

### Workflow 2 wording cleanup

Cleaned up wording for Workflow 2 recommended actions.

Included:

- Recommended action wording cleaned up.
- No business logic changes intended.

No HubSpot integration, LLM calls, n8n automation, meeting platform integration, or external API calls were added.

### Workflow 2 summary endpoint implemented

Implemented the first deterministic version of Workflow 2: Meeting Capture and CRM Summary.

Included:

- Pydantic models added for meeting summary requests, responses, and recommended actions.
- Deterministic meeting summary service added.
- `recommended_actions` added to the response model.
- `/ai/summarize-meeting` now returns structured output.
- Local test script added for the meeting summary golden dataset.

No HubSpot integration, LLM calls, n8n automation, meeting platform integration, or external API calls were added yet.

### Workflow 2 next-step action plan added

Updated the Workflow 2 design to include a next-step action plan.

Included:

- `recommended_actions` added to expected results.
- SOP updated to separate auto-allowed internal actions from review-required actions.

No endpoint logic, HubSpot integration, LLM calls, n8n automation, meeting platform integration, or external API calls were added.

### Workflow 2 review policy tightened

Tightened the Workflow 2 expected results to better match the human review policy.

Included:

- Expected results now better match the human review policy.
- Deal stage recommendations and missing-information cases require review.

No endpoint logic, HubSpot integration, LLM calls, meeting platform integration, n8n automation, or external API calls were added.

### Workflow 2 design foundation added

Added the design foundation for Workflow 2: Meeting Capture and CRM Summary.

Included:

- SOP created.
- Workflow map updated.
- Meeting capture/minutes source documented.
- Synthetic meeting transcripts and minutes created.
- Expected summary results created for future deterministic extraction tests.

No real AI logic, CRM integration, meeting platform integration, HubSpot integration, n8n automation, or external API calls were added yet.

### Workflow 1 Version 1 verified

Verified Workflow 1 Version 1 for Lead Scoring and Routing.

Included:

- Lead scoring test script passed with 8 passed, 0 failed.
- Blank required field validation was tested and failed correctly.
- This confirms the workflow can score valid sample leads and reject bad input.

No HubSpot integration, LLM calls, n8n automation, database, or external API calls were added.

### Workflow 1 code cleanup

Completed a small code cleanup pass for Workflow 1.

Included:

- Response types tightened for confidence and urgency.
- Basic validation added for required lead scoring request text fields.
- Scoring service documented.
- Workflow name constant added for future observability.

No HubSpot integration, LLM calls, n8n automation, database, or external API calls were added.

### Operational guardrails documented

Documented project-wide operational guardrails.

Included:

- Observability.
- Data integrity.
- Security.
- Authentication and access control.
- Human review.
- Failure handling.

No workflow features, HubSpot integration, LLM calls, n8n automation, or external API calls were added.

### Workflow 1 scoring quality pass

Improved the quality checks and scoring calibration for Workflow 1.

Included:

- Test script now checks priority, human review flag, confidence, urgency, and score range.
- Scoring rules tuned against the golden dataset.
- Pain points, routes, next actions, and reasoning remain informational for now.

No HubSpot integration, LLM calls, n8n automation, or external API calls were added.

### Workflow 1 scoring endpoint implemented

Implemented the first deterministic version of Workflow 1: Lead Scoring and Routing.

Included:

- Pydantic models added for lead scoring requests and responses.
- Deterministic scoring service added.
- `/ai/score-lead` now returns real scoring output.
- Local test script added for the golden lead dataset.

No HubSpot integration, LLM calls, n8n automation, or external API calls were added yet.

### Workflow 1 data strategy clarified

Clarified the Workflow 1 lead data strategy.

Included:

- Golden test dataset kept small.
- The 8 synthetic leads remain the source of truth for proving scoring logic.
- Larger demo dataset deferred until scoring logic works.

No endpoint logic, HubSpot integration, LLM calls, or external API calls were added.

### Workflow 1 design foundation added

Added the design foundation for Workflow 1: Lead Scoring and Routing.

Included:

- SOP created for lead scoring and routing.
- Workflow map updated with the Workflow 1 design.
- Synthetic lead data created.
- Expected scoring results created for future deterministic scoring tests.

No real AI logic, CRM integration, HubSpot integration, n8n automation, or external API calls were added yet.

### Foundation verified locally

Verified the foundation in a local development environment:

- FastAPI app runs locally.
- `GET /health` returns project status.
- API docs show placeholder workflow routes.
- Next.js dashboard loads locally.
- No external services are connected yet.
- No real AI logic has been implemented yet.

### Foundation cleanup pass

Added a placeholder API surface for future sales automation workflows:

- `POST /ai/score-lead`
- `POST /ai/summarize-meeting`
- `POST /ai/draft-follow-up`
- `POST /ai/check-crm-hygiene`
- `POST /ai/draft-proposal`
- `POST /ai/ask-sales-kb`
- `GET /logs`
- `POST /logs/ai-action`
- `GET /metrics/dashboard`

Updated documentation to reinforce a documentation-first approach:

- Foundation scaffold created.
- Placeholder API surface added.
- Documentation-first approach established.

No real AI logic, HubSpot integration, external API calls, authentication, or real secrets were added.

### Initial scaffold

Created the foundation for `revenue-ai-automation-suite`.

Included:

- Repository structure.
- FastAPI app with `/health`.
- pydantic-settings configuration.
- Next.js App Router dashboard shell.
- Placeholder sales operations pages.
- Starter components.
- Documentation set.
- Empty future-work areas for SOPs, knowledge base, sample data, and n8n.

Not included:

- Real AI logic.
- HubSpot integration.
- External API calls.
- Authentication.
- Real secrets.
