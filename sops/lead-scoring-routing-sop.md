# Lead Scoring and Routing SOP

## Purpose

This workflow helps sales teams sort new leads by intent, fit, urgency, and routing needs. The goal is to help reps focus on the right leads sooner without letting automation make final judgment calls too early.

## Trigger

The workflow should run when a new lead is created or when an existing lead submits a new high-intent form, such as a demo request, pricing request, implementation question, or contact form.

## Inputs

The workflow may use:

- Lead name and email.
- Company name.
- Role or title.
- Company size.
- Lead source.
- Submitted message.
- Buying timeline.
- Budget signal.
- Current CRM or sales tool.
- Date the lead was created.

Only approved CRM and form data should be used. No private notes or sensitive fields should be included unless the team has approved that use.

## Outputs

The workflow should produce:

- Lead score.
- Priority level.
- Persona.
- Main pain points.
- Urgency level.
- Recommended route.
- Next best action.
- Confidence level.
- Human review flag.
- Short reasoning.

## Scoring Approach

Start with simple rules before using AI:

- Give more weight to demo requests, urgent timelines, clear pain, and clear budget.
- Give moderate weight to good-fit roles, company size, and relevant CRM context.
- Reduce the score for vague messages, missing information, student requests, test submissions, or spam-like leads.
- Keep the reasoning short so a sales rep can understand why the score was assigned.

The first implementation should be deterministic and testable with sample data. AI can be added later only if the rule-based version is understood and useful.

## Lead Data Strategy

`sample-data/leads.json` is the golden test dataset for Workflow 1. It contains 8 carefully chosen synthetic leads that cover the main cases the scoring logic needs to handle.

These leads are used to prove that the scoring logic works before the project adds more volume or visual polish. Each golden lead has a matching expected result so future deterministic tests can compare actual scoring output against a known answer.

A larger demo dataset of 30-40 leads will be added later for dashboard realism and volume testing. That larger dataset does not need hand-written expected results for every lead. It is meant to make the dashboard feel realistic, while the 8-lead golden dataset is meant to prove the scoring rules.

## Priority Levels

- `critical`: The lead shows urgent need, strong fit, and clear buying or implementation intent. A rep should respond as soon as possible, and a human should review the route before any CRM-changing action.
- `high`: The lead is a strong fit with clear pain, intent, and next-step potential. It should be routed quickly to the right sales owner.
- `medium`: The lead has some useful fit or pain signals but may have budget, timing, size, or clarity limits. It should be worked, qualified, or nurtured based on context.
- `low`: The lead has weak intent, vague need, or limited fit. It should not distract reps from stronger opportunities and may be routed to nurture.
- `disqualify`: The lead appears to be a test, student request, spam-like submission, or clearly outside the sales motion. It should not be routed to active sales follow-up unless a human reviewer sees a reason to override.

## Human Review Rules

Human review should be required when:

- The lead is enterprise-sized but missing important information.
- The score is high but confidence is low.
- The lead asks for pricing, legal terms, or a complex implementation.
- The submission looks like a student, test, or spam lead.
- The recommended route would change ownership or priority in the CRM.

## Auto-Update Rules

At this stage, there should be no automatic CRM updates.

Later, low-risk updates may be allowed only after the team agrees on rules. Examples could include adding a draft score, adding a suggested route, or creating a review task. Any update that changes lead ownership, lifecycle stage, or customer-facing communication should require human approval.

## Failure Handling

If required fields are missing, the workflow should return a low-confidence result and route the lead for review.

If scoring cannot run, the lead should remain unchanged and a log entry should explain the failure. The sales team should still be able to work the lead manually.

## Success Metrics

Track whether the workflow helps the team:

- Respond faster to high-priority leads.
- Reduce time spent manually sorting inbound leads.
- Improve routing accuracy.
- Catch urgent or high-fit leads earlier.
- Avoid wasting rep time on test or spam-like submissions.
- Maintain trust through clear reasoning and review controls.

## Owner/Maintenance Notes

The revenue operations owner should maintain the scoring rules with input from sales leadership and frontline reps.

Rules should be reviewed regularly, especially when the sales motion, ideal customer profile, CRM process, or routing model changes.
