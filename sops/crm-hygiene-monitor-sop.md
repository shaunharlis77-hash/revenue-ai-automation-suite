# CRM Hygiene / Deal Risk Monitor SOP

## Purpose

This workflow checks CRM and deal records for missing information, stale activity, risky deal conditions, and required rep actions.

The goal is to help sales managers and RevOps owners spot problems early without letting automation change CRM data on its own.

## Trigger

The workflow may run on a schedule, before pipeline review, or when a deal reaches an important stage.

## Inputs

The workflow may use:

- Record ID.
- Lead ID.
- Deal ID.
- Company and contact name.
- Deal stage.
- Lead priority.
- Owner.
- Last activity date.
- Next step and next-step due date.
- Follow-up due date.
- Proposal status.
- Human review status.
- Required CRM fields.
- Open risks.
- Days in stage.
- Deal value band.

## Outputs

The workflow should produce:

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

## Monitoring Approach

The first version uses deterministic rules only. It checks for common CRM hygiene problems such as missing owner, missing next step, stale activity, missing follow-up, pending proposal review, long stage age, and missing required CRM fields.

The workflow does not update CRM records directly.

## Human Review Rules

Human review is required when risk is high or critical.

Review is also required when a proposal is pending and human review is incomplete, or when ownership is missing and the deal needs manager or RevOps attention.

## Auto-Update Rules

At this stage, the workflow must not write to CRM.

It may identify issues, recommend actions, and log the workflow result. Future CRM updates should require clear approval rules.

## Failure Handling

If required input is missing, the workflow should fail before producing a hygiene result.

If processing fails, the workflow should log the failed step and reason, leave CRM unchanged, and allow the owner or RevOps team to review the record manually.

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

- Reduce missing CRM fields.
- Catch stale deals earlier.
- Keep high-priority leads from going untouched.
- Improve proposal review visibility.
- Give managers clearer deal risk signals.

## Owner/Maintenance Notes

Revenue operations should maintain the hygiene rules with input from sales leadership.

Thresholds such as stale activity days and days-in-stage limits should be reviewed as the sales process changes.
