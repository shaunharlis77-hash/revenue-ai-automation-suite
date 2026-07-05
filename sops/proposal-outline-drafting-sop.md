# Proposal / Package Outline Drafting SOP

## Purpose

This workflow prepares an internal proposal or package outline for sales rep review. It helps reps organize discovery context into a useful structure without creating a final customer-ready proposal automatically.

## Trigger

The workflow should run after enough lead, meeting, and follow-up context is available to prepare a package outline.

## Inputs

The workflow may use:

- Proposal ID.
- Lead, meeting, and follow-up IDs.
- Rep, contact, and company names.
- Deal stage recommendation.
- Lead priority.
- Pain points.
- Objections.
- Buying signals.
- Next steps.
- Requested package type.
- Budget context.
- Implementation timeline.
- Current CRM.
- Risk areas.

## Outputs

The workflow should produce:

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

## Drafting Approach

The first version uses deterministic rules only. It creates a concise internal outline based on provided context.

The outline must not invent pricing, scope, legal terms, security claims, compliance claims, or implementation commitments.

## Human Review Rules

Human review is always required because the outline may become customer-facing later.

Review is especially important when the outline includes:

- Pricing or budget concerns.
- Security or legal review.
- Implementation timing or scope.
- Adoption or change management risk.
- Missing budget, timeline, pain points, or next steps.

## Auto-Update Rules

The workflow must not send a proposal, email, or message automatically.

It may prepare an internal outline, add risk notes, recommend next action, and log the workflow result. Any customer-facing use requires rep approval.

## Failure Handling

If required input is missing, the workflow should fail before creating an outline.

If drafting fails, the workflow should log the failed step and reason, require human review, and allow the rep to create the outline manually.

## Observability

Each run should log:

- Workflow run ID.
- Workflow name.
- Status.
- Input reference.
- Output summary.
- Whether human review is required.
- Next action.
- Failure step and reason when applicable.

## Success Metrics

Track whether the workflow helps the team:

- Prepare proposal outlines faster.
- Keep package recommendations tied to discovery context.
- Avoid unsafe promise language.
- Surface risk areas before customer-facing use.
- Maintain human approval for proposal work.

## Owner/Maintenance Notes

Revenue operations and sales leadership should maintain the outline rules together.

Pricing, legal, security, and implementation language should be reviewed regularly so the workflow stays aligned with current policy.
