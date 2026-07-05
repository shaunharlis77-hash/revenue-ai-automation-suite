# Follow-Up Drafting SOP

## Purpose

This workflow prepares a customer-facing follow-up draft after a meeting or sales interaction. The goal is to save rep writing time while keeping the rep in control of anything that goes to a prospect or customer.

## Trigger

The workflow should run after meeting summary context is available and a rep needs a follow-up message.

## Inputs

The workflow may use:

- Follow-up ID.
- Lead ID.
- Meeting ID.
- Rep and contact names.
- Company.
- Lead priority.
- Deal stage recommendation.
- Pain points.
- Objections.
- Buying signals.
- Next steps.
- Follow-up due timing.
- Message channel.
- Tone.

Only approved meeting and sales context should be used. The workflow should not invent facts that are not present in the input.

## Outputs

The workflow should produce:

- Draft subject.
- Draft body.
- Message channel.
- Tone.
- Source context summary.
- Review required flag.
- Review reasons.
- Risk notes.
- Recommended send timing.
- Next action.
- Confidence.
- Reasoning.

## Drafting Approach

The first version uses deterministic rules only. It turns structured meeting context into a simple business-friendly draft.

The draft should reference the meeting context naturally, include agreed next steps when they are clear, and ask the rep to confirm details when next steps are missing.

## Human Review Rules

Human review is always required because the output is customer-facing.

Review is especially important when the draft touches:

- Pricing.
- Legal terms.
- Security.
- Implementation scope or timing.
- Adoption or change management concerns.
- Missing or unclear next steps.

## Auto-Update Rules

The workflow must not send any email, WhatsApp message, or other customer-facing communication automatically.

It may prepare a draft, add a review item, and log the workflow result. Sending requires rep approval.

## Failure Handling

If required input is missing, the workflow should fail before drafting and leave customer communication unchanged.

If drafting fails, the workflow should log the failed step and reason, require human review, and allow the rep to write the follow-up manually.

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

- Draft follow-ups faster.
- Keep messages aligned to meeting context.
- Avoid risky promise language.
- Reduce missed next steps.
- Maintain human approval for customer-facing work.

## Owner/Maintenance Notes

Revenue operations should maintain the drafting rules with input from sales reps and sales leadership.

Risk language should be reviewed regularly so the workflow stays aligned with pricing, legal, security, and implementation policies.
