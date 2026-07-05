# AI Roadmap

## Stage 1: Foundation

Create the project structure, backend health check, dashboard layout, documentation, and placeholder workflow areas.

Status: in progress.

## Stage 2: Synthetic Workflow Prototypes

Use sample data to prototype workflow behavior without connecting to live systems. Examples may include mock lead scoring, mock meeting summaries, and mock review queues.

## Stage 3: Human Review Layer

Add approval states, reviewer notes, audit history, and clear labels for AI-assisted content.

## Stage 4: Controlled Integrations

Add HubSpot and n8n integration in a limited way. Start with read-only or sandbox data before any write-back.

## Stage 5: AI-Assisted Workflows

Introduce AI services for specific use cases after prompts, data boundaries, review policies, and failure modes are documented.

## Guardrails

- Do not send customer-facing messages automatically.
- Do not write to CRM without approval.
- Do not rely on AI outputs without source context.
- Do not store secrets in the repository.

