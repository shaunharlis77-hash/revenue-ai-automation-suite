# Meeting Capture and CRM Summary SOP

## Purpose

This workflow helps sales reps turn meeting notes or transcripts into a clear CRM-ready summary.

The goal is to reduce post-call admin while keeping the rep in control of anything that affects customers, deals, or CRM records.

Workflow 2 has two stages:

1. Meeting Capture / Minutes Agent
2. Meeting Summary to CRM Update

## Trigger

The workflow should run after a sales meeting when meeting content is available.

For the prototype, the meeting content comes from manual notes or synthetic sample transcripts. Later, meeting content could come from Microsoft Teams, Google Meet, Zoom, or another meeting notes tool.

## Inputs

The workflow may use:

- Meeting ID.
- Lead ID.
- Deal ID.
- Rep name.
- Contact name.
- Company.
- Meeting date.
- Meeting source.
- Source platform.
- Transcript type.
- Transcript, meeting minutes, or rough notes.

The summary workflow should not depend on a specific meeting platform.

## Outputs

The workflow should produce:

- CRM note.
- Pain points.
- Objections.
- Buying signals.
- Next steps.
- Follow-up due date or timing.
- Deal stage recommendation.
- Proposal needed flag.
- Confidence level.
- Human review flag.
- Needs more information flag.
- Short reasoning.

## Meeting Capture Source

The prototype uses manual or sample meeting content stored in `sample-data/meeting-transcripts.json`.

Later, a meeting capture or minutes agent could plug into:

- Microsoft Teams.
- Google Meet.
- Zoom.
- Another meeting recorder or notes tool.

The capture layer should only provide meeting content. The CRM summary workflow should still work the same way no matter where the content came from.

## Summary Approach

Start with simple extraction rules before using AI:

- Identify pain points mentioned by the prospect.
- Identify objections or concerns.
- Identify buying signals.
- Capture next steps.
- Flag whether a proposal is needed.
- Recommend a CRM note and possible deal stage.
- Mark low-quality notes as low confidence.

The first implementation should be deterministic and testable with sample meeting content. AI can be added later once the basic extraction shape is clear.

## Next-Step Action Plan

The workflow should prepare the next sales actions after a meeting, not only summarize what happened.

Low-risk internal actions can be prepared or created automatically. Risky actions should still be prepared, but they should be routed for review instead of being ignored. The rep should review and approve prepared work rather than start from scratch.

Auto-allowed internal actions:

- Prepare CRM note.
- Create rep follow-up task.
- Set follow-up due date.
- Flag missing information.
- Add item to review queue.
- Log workflow result.

Review-required actions:

- Send customer-facing message.
- Change deal stage.
- Change deal owner.
- Mark proposal/quote as ready.
- Use pricing, legal, security, or implementation claims.
- Handle low-confidence summaries.
- Handle missing-information cases.

## Human Review Rules

A CRM note can be prepared automatically as a draft. Deal stage changes, proposal flags, missing-information cases, and customer-facing follow-ups require human review.

Human review should be required when:

- The transcript is poor or too short.
- Budget, timeline, owner, or next step is unclear.
- The summary recommends a deal stage change.
- A proposal draft is needed.
- A customer-facing follow-up is created.
- The meeting includes pricing, legal, security, or implementation risk.

Customer-facing follow-ups and proposal drafts always require human review before use.

## Auto-Update Rules

At this stage, there should be no automatic CRM updates.

Later, low-risk draft notes may be prepared for review. Updates to deal stage, next steps, ownership, proposal status, or customer-facing communication should require approval.

## Failure Handling

If the meeting content is missing or too weak, the workflow should return a low-confidence result and route it for review.

If summary generation cannot run, leave CRM unchanged, log the failure, and allow the rep to write the meeting note manually.

## Success Metrics

Track whether the workflow helps the team:

- Reduce time spent writing CRM notes.
- Improve consistency of meeting summaries.
- Capture next steps more reliably.
- Identify objections and buying signals earlier.
- Reduce missed follow-ups.
- Keep customer-facing work under human review.

## Owner/Maintenance Notes

The revenue operations owner should maintain the expected summary structure with input from sales reps and managers.

Rules should be reviewed when the sales process, deal stages, meeting format, or CRM note standards change.
