# Architecture

## Overview

The project is organized as a small multi-app workspace:

- `apps/web`: Next.js dashboard for internal sales operations users.
- `apps/api`: FastAPI backend for future workflow orchestration and data access.
- `workflows/n8n`: Future n8n workflow definitions and notes.
- `knowledge-base`: Future approved sales knowledge.
- `sample-data`: Future synthetic data for demos and development.
- `docs`: Project decisions and operating context.

## Current Flow

There is no live data flow yet. The web app uses placeholder data only. The API exposes a simple `/health` endpoint so the backend can be started and checked.

## Future Flow

A future version may work like this:

1. HubSpot provides sales and CRM context.
2. n8n triggers or coordinates workflow steps.
3. FastAPI validates requests, applies business rules, and coordinates services.
4. AI services assist with summaries, drafts, classification, or recommendations.
5. The web dashboard presents outputs for human review.
6. Approved results are sent, stored, or written back to HubSpot.

## Operational Guardrails Layer

Observability, data integrity, security, authentication, and human review sit across every workflow.

This means each workflow should show whether it ran, whether it succeeded, where it failed, and what should happen next. It also means CRM data should stay protected, risky actions should require review, and access should eventually depend on user roles.

## Design Principle

The architecture should make automation useful without making it invisible. Reviewers should understand what happened, why it happened, and what requires approval.
