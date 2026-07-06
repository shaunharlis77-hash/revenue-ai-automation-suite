from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.database import decode_json, get_connection
from app.services.hubspot_adapter import get_hubspot_status


AVAILABLE_AI_WORKFLOWS = {
    "lead_intake": "lead_intake_enrichment",
    "lead_scoring": "lead_scoring_routing",
    "meeting_summary": "meeting_capture_crm_summary",
    "follow_up": "follow_up_drafting",
    "proposal": "proposal_outline_drafting",
    "crm_hygiene": "crm_hygiene_deal_risk_monitor",
    "hubspot_sync": "hubspot_sync",
}

TIME_SAVED_MINUTES = {
    "safe_crm_update": 5,
    "lead_scoring_routing": 4,
    "lead_intake_enrichment": 4,
    "meeting_capture_crm_summary": 10,
    "follow_up_drafting": 8,
    "proposal_outline_drafting": 15,
    "crm_hygiene_deal_risk_monitor": 6,
    "hubspot_sync": 5,
}


def get_sales_manager_dashboard_metrics() -> dict[str, Any]:
    data = load_dashboard_data()
    crm_records = data["crm_records"]
    audit_events = data["audit_events"]
    review_items = data["review_items"]
    workflow_runs = data["workflow_runs"]

    sales_overview = build_sales_overview(data)
    lead_health = build_lead_and_pipeline_health(data)
    drop_off_stats = build_drop_off_zone_stats(data)
    adoption = build_team_activity_and_ai_adoption(data)
    ai_impact = build_ai_impact(data)
    sales_risks = build_sales_execution_risks(data, drop_off_stats)

    return {
        "sales_overview": sales_overview,
        "lead_and_pipeline_health": lead_health,
        "drop_off_zone_stats": drop_off_stats,
        "team_activity_and_ai_adoption": adoption,
        "ai_impact": ai_impact,
        "sales_execution_risks": sales_risks,
        "recent_revenue_activity": build_recent_revenue_activity(
            audit_events, crm_records, review_items, workflow_runs
        ),
    }


def get_admin_dashboard_metrics() -> dict[str, Any]:
    data = load_dashboard_data()
    status = get_hubspot_status()
    workflow_runs = data["workflow_runs"]
    crm_records = data["crm_records"]
    step_events = data["step_events"]
    review_items = data["review_items"]
    audit_events = data["audit_events"]

    recent_sync_records = [
        record
        for record in sorted(
            crm_records,
            key=lambda item: item.get("last_hubspot_sync_at") or item.get("updated_at") or "",
            reverse=True,
        )
        if record.get("hubspot_sync_status")
    ]

    return {
        "system_status": {
            "adapter_mode": status.adapter_mode,
            "hubspot_enabled": status.hubspot_enabled,
            "hubspot_configured": status.token_configured,
            "last_hubspot_sync_at": first_value(recent_sync_records, "last_hubspot_sync_at"),
            "recent_sync_status": first_value(recent_sync_records, "hubspot_sync_status"),
            "total_workflow_runs": len(workflow_runs),
            "failed_workflow_runs": count_where(workflow_runs, "status", "failed"),
            "partial_workflow_runs": count_partial_workflow_runs(crm_records),
            "open_review_items": count_where(review_items, "status", "pending"),
            "operational_failures_last_24h": count_recent_failures(step_events),
        },
        "review_queue_health": build_review_queue_health(review_items),
        "audit_health": build_audit_health(audit_events),
        "operational_health": build_operational_health(step_events),
        "hubspot_sync_health": build_hubspot_sync_health(crm_records),
        "workflow_health": build_workflow_health(workflow_runs, crm_records),
        "action_links": [
            {"label": "Review Queue", "route": "/review-queue"},
            {"label": "Audit Trail", "route": "/audit-trail"},
            {"label": "Operational Logs", "route": "/operational-logs"},
            {"label": "CRM Records", "route": "/crm-records"},
            {"label": "HubSpot Status", "route": "/hubspot-status"},
            {"label": "Lead Intake", "route": "/lead-intake"},
        ],
    }


def load_dashboard_data() -> dict[str, list[dict[str, Any]]]:
    with get_connection() as connection:
        return {
            "workflow_runs": rows_to_dicts(
                connection.execute("SELECT * FROM workflow_runs ORDER BY id ASC").fetchall()
            ),
            "audit_events": rows_to_dicts(
                connection.execute("SELECT * FROM audit_events ORDER BY id ASC").fetchall()
            ),
            "review_items": rows_to_dicts(
                connection.execute("SELECT * FROM review_items ORDER BY id ASC").fetchall()
            ),
            "step_events": rows_to_dicts(
                connection.execute(
                    "SELECT * FROM workflow_step_events ORDER BY id ASC"
                ).fetchall()
            ),
            "crm_records": rows_to_dicts(
                connection.execute("SELECT * FROM crm_lead_records ORDER BY id ASC").fetchall()
            ),
            "crm_activities": rows_to_dicts(
                connection.execute("SELECT * FROM crm_activities ORDER BY id ASC").fetchall()
            ),
        }


def rows_to_dicts(rows) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def build_sales_overview(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    records = data["crm_records"]
    audit_events = data["audit_events"]
    review_items = data["review_items"]
    workflow_runs = data["workflow_runs"]
    time_saved = estimate_time_saved_minutes(data)

    return {
        "total_leads_processed": len(records),
        "high_priority_leads": count_priorities(records, {"high", "critical"}),
        "medium_priority_leads": count_priorities(records, {"medium"}),
        "low_priority_leads": count_priorities(records, {"low"}),
        "disqualified_or_low_fit_leads": count_priorities(records, {"disqualify"}),
        "crm_updates_applied": count_crm_updates_applied(records),
        "crm_updates_blocked": count_where(records, "crm_update_status", "blocked_pending_review"),
        "open_review_items_affecting_sales": count_where(review_items, "status", "pending"),
        "proposals_recommended": count_events(audit_events, {"proposal_outline_created"}),
        "follow_ups_drafted": count_events(audit_events, {"follow_up_draft_created"}),
        "meeting_summaries_created": count_events(audit_events, {"meeting_summary_created"}),
        "estimated_time_saved_minutes": time_saved,
        "estimated_time_saved_hours": round(time_saved / 60, 1),
        "source_workflow_runs": len(workflow_runs),
    }


def build_lead_and_pipeline_health(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    records = data["crm_records"]
    review_items = data["review_items"]

    return {
        "lead_priority_breakdown": counter_dict(record.get("priority") for record in records),
        "leads_by_persona": counter_dict(record.get("enriched_persona") for record in records),
        "leads_by_route": counter_dict(record.get("recommended_route") for record in records),
        "latest_high_priority_leads": [
            lead_summary(record)
            for record in sorted(records, key=lambda item: item.get("created_at") or "", reverse=True)
            if str(record.get("priority")).lower() in {"high", "critical"}
        ][:5],
        "records_pending_review": count_where(review_items, "status", "pending"),
        "records_blocked_pending_review": count_where(records, "crm_update_status", "blocked_pending_review"),
        "stale_or_at_risk_records": count_risky_records(records),
        "missing_next_step_count": count_missing_next_step(records),
        "overdue_follow_up_count": not_enough_data(
            "Follow-up due dates are not stored on CRM records yet."
        ),
    }


def build_drop_off_zone_stats(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    records = data["crm_records"]
    review_items = data["review_items"]
    audit_events = data["audit_events"]

    high_priority_without_follow_up = [
        record for record in records if str(record.get("priority")).lower() in {"high", "critical"}
    ]
    blocked_records = [
        record for record in records if record.get("crm_update_status") == "blocked_pending_review"
    ]
    missing_next_step_records = [
        record for record in records if missing_or_unclear(record.get("next_best_action"))
    ]
    stale_records = [
        record for record in records if record_risk_flags(record)
    ]
    proposal_pending_items = [
        item
        for item in review_items
        if item.get("status") == "pending"
        and "proposal" in str(item.get("review_type", "")).lower()
    ]
    failed_or_partial_hubspot = [
        record
        for record in records
        if record.get("hubspot_sync_status") in {"failed", "partial_sync"}
    ]

    zones = [
        drop_zone(
            "High-priority lead without follow-up",
            len(high_priority_without_follow_up),
            "high",
            [record.get("lead_id") for record in high_priority_without_follow_up],
            "Assign owner and follow up today",
        ),
        drop_zone(
            "Proposal prepared but pending review",
            len(proposal_pending_items),
            "medium",
            [item.get("review_item_id") for item in proposal_pending_items],
            "Review pending proposal",
        ),
        drop_zone(
            "CRM update blocked pending review",
            len(blocked_records),
            "high",
            [record.get("crm_record_id") for record in blocked_records],
            "Approve or reject blocked CRM update",
        ),
        drop_zone(
            "HubSpot sync failed or partially synced",
            len(failed_or_partial_hubspot),
            "medium",
            [record.get("crm_record_id") for record in failed_or_partial_hubspot],
            "Check HubSpot sync issue",
        ),
        drop_zone(
            "Deal or record has no next step",
            len(missing_next_step_records),
            "medium",
            [record.get("crm_record_id") for record in missing_next_step_records],
            "Add next step before next sales meeting",
        ),
        drop_zone(
            "Deal or record stale",
            len(stale_records),
            "medium",
            [record.get("crm_record_id") for record in stale_records],
            "Coach rep on follow-up discipline",
        ),
    ]
    zones.extend(
        [
            unavailable_drop_zone(
                "Lead captured but not scored",
                "Lead capture events before scoring are not stored separately yet.",
            ),
            unavailable_drop_zone(
                "Lead scored but not routed",
                "Routing is stored as part of scored CRM records, not as a separate stage.",
            ),
            unavailable_drop_zone(
                "Meeting summarized but no follow-up drafted",
                "Meeting-to-follow-up linkage is not persisted yet.",
            ),
            unavailable_drop_zone(
                "Proposal recommended but not prepared",
                "Proposal recommendation-to-creation linkage is not persisted yet.",
            ),
            unavailable_drop_zone(
                "Review item pending too long",
                "Review SLA age thresholds are not configured yet.",
            ),
        ]
    )

    drop_counts = [zone for zone in zones if isinstance(zone.get("count"), int)]
    drop_by_reason = {
        zone["zone_name"]: zone["count"] for zone in drop_counts if zone["count"] > 0
    }

    return {
        "total_drop_off_signals": sum(zone["count"] for zone in drop_counts),
        "drop_off_by_stage": drop_by_reason,
        "drop_off_by_reason": drop_by_reason,
        "drop_off_by_rep_or_owner": not_enough_data(
            "Owner or rep attribution is not consistently stored yet."
        ),
        "high_priority_leads_without_follow_up": len(high_priority_without_follow_up),
        "meeting_completed_no_follow_up": not_enough_data(
            "Meeting-to-follow-up linkage is not persisted yet."
        ),
        "proposal_recommended_not_created": not_enough_data(
            "Proposal recommendation-to-creation linkage is not persisted yet."
        ),
        "proposal_created_pending_review": len(proposal_pending_items),
        "crm_update_blocked_pending_review": len(blocked_records),
        "hubspot_sync_failed_or_partial": len(failed_or_partial_hubspot),
        "missing_next_step": len(missing_next_step_records),
        "stale_records": len(stale_records),
        "overdue_follow_ups": not_enough_data(
            "Follow-up due dates are not stored on CRM records yet."
        ),
        "records_with_open_risks": count_risky_records(records),
        "top_drop_off_zones": sorted(
            zones,
            key=lambda zone: zone["count"] if isinstance(zone.get("count"), int) else -1,
            reverse=True,
        )[:8],
        "audit_event_count_used": len(audit_events),
    }


def build_team_activity_and_ai_adoption(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    workflow_runs = data["workflow_runs"]
    audit_events = data["audit_events"]
    used = used_workflow_keys(workflow_runs, audit_events)
    available = list(AVAILABLE_AI_WORKFLOWS.keys())
    usage_breakdown = workflow_usage_breakdown(workflow_runs, audit_events)
    last_activity = latest_timestamp(workflow_runs + audit_events)

    return {
        "ai_assisted_workflows_used": len(used),
        "available_ai_workflows": available,
        "workflow_usage_breakdown": usage_breakdown,
        "adoption_rate_percent": percent(len(used), len(available)),
        "total_ai_assisted_actions": sum(usage_breakdown.values()),
        "most_used_ai_workflow": top_counter_key(usage_breakdown),
        "least_used_ai_workflow": least_counter_key(usage_breakdown, available),
        "last_ai_activity_at": last_activity,
        "rep_adoption_status": "not_enough_rep_level_data",
        "rep_level_recommendation": (
            "Add owner/rep attribution to workflow runs and CRM records to unlock "
            "rep-level AI adoption reporting."
        ),
        "active_reps_with_ai_activity": not_enough_data(
            "Rep attribution is not consistently stored yet."
        ),
        "total_reps_seen": not_enough_data(
            "Rep attribution is not consistently stored yet."
        ),
        "rep_adoption_rate_percent": not_enough_data(
            "Rep attribution is not consistently stored yet."
        ),
        "ai_activity_by_rep": [],
        "ai_workflows_used_by_rep": [],
        "estimated_time_saved_by_rep": [],
        "approvals_by_rep": [],
        "rejected_ai_outputs_by_rep": [],
        "last_ai_activity_by_rep": [],
        "reps_with_no_recent_ai_activity": [],
        "top_ai_users": [],
        "reps_needing_enablement": [],
    }


def build_ai_impact(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    records = data["crm_records"]
    review_items = data["review_items"]
    audit_events = data["audit_events"]
    time_saved = estimate_time_saved_minutes(data)
    safe_count = count_crm_updates_applied(records)
    human_review_count = count_distinct_review_required_actions(review_items, audit_events)
    blocked_count = count_events(
        audit_events,
        {"crm_update_blocked", "hubspot_sync_blocked", "crm_adapter_write_blocked"},
    ) + count_where(records, "crm_update_status", "blocked_pending_review")
    approved = count_where(review_items, "status", "approved")
    rejected = count_where(review_items, "status", "rejected")
    total_reviews_decided = approved + rejected
    total_actions = max(len(audit_events), 1)

    return {
        "safe_automation_count": safe_count,
        "human_review_required_count": human_review_count,
        "blocked_action_count": blocked_count,
        "ai_outputs_approved_count": approved,
        "ai_outputs_rejected_count": rejected,
        "ai_approval_rate_percent": percent(approved, total_reviews_decided),
        "automation_rate_percent": percent(safe_count, total_actions),
        "review_rate_percent": percent(human_review_count, total_actions),
        "block_rate_percent": percent(blocked_count, total_actions),
        "estimated_time_saved_minutes": time_saved,
        "estimated_time_saved_hours": round(time_saved / 60, 1),
        "estimation_method": {
            "safe_crm_update": "5 minutes saved",
            "lead_scoring_or_routing": "4 minutes saved",
            "meeting_summary": "10 minutes saved",
            "follow_up_draft": "8 minutes saved",
            "proposal_outline": "15 minutes saved",
            "crm_hygiene_check": "6 minutes saved",
            "hubspot_sync": "5 minutes saved",
            "label": "Estimated, not actual tracked time.",
        },
    }


def build_sales_execution_risks(
    data: dict[str, list[dict[str, Any]]], drop_off_stats: dict[str, Any]
) -> dict[str, Any]:
    records = data["crm_records"]
    review_items = data["review_items"]
    top_risk_reasons = Counter()
    for item in review_items:
        for reason in json_list(item.get("review_reasons")):
            top_risk_reasons[human_label(reason)] += 1
    for record in records:
        for flag in record_risk_flags(record):
            top_risk_reasons[human_label(flag)] += 1

    return {
        "pending_reviews": count_where(review_items, "status", "pending"),
        "blocked_crm_updates": count_where(records, "crm_update_status", "blocked_pending_review"),
        "stale_deals_or_records": drop_off_stats["stale_records"],
        "missing_next_steps": drop_off_stats["missing_next_step"],
        "failed_or_partial_hubspot_syncs_affecting_sales": drop_off_stats[
            "hubspot_sync_failed_or_partial"
        ],
        "high_priority_leads_needing_attention": drop_off_stats[
            "high_priority_leads_without_follow_up"
        ],
        "reps_with_low_ai_usage": not_enough_data(
            "Rep attribution is not consistently stored yet."
        ),
        "top_risk_reasons": [
            {"reason": reason, "count": count}
            for reason, count in top_risk_reasons.most_common(8)
        ],
    }


def build_recent_revenue_activity(
    audit_events: list[dict[str, Any]],
    records: list[dict[str, Any]],
    review_items: list[dict[str, Any]],
    workflow_runs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    record_by_lead = {record.get("lead_id"): record for record in records}
    review_by_entity = {item.get("entity_id"): item for item in review_items}
    activity = []
    for event in sorted(audit_events, key=lambda item: item.get("created_at") or "", reverse=True):
        label = sales_manager_label(event.get("event_type", ""))
        if not label:
            continue
        entity_id = event.get("entity_id")
        record = record_by_lead.get(entity_id, {})
        review = review_by_entity.get(entity_id, {})
        activity.append(
            {
                "timestamp": event.get("created_at"),
                "event_type": event.get("event_type"),
                "workflow_name": event.get("workflow_name"),
                "entity_type": event.get("entity_type"),
                "entity_id": entity_id,
                "company": record.get("company") or review.get("company"),
                "contact": record.get("contact_name") or review.get("contact_name"),
                "owner_or_rep": review.get("assigned_to"),
                "business_action": label,
                "status": status_from_event(event.get("event_type", "")),
                "human_review_required": bool(event.get("human_review_required")),
                "sales_manager_label": label,
            }
        )
    if not activity and workflow_runs:
        for run in sorted(workflow_runs, key=lambda item: item.get("created_at") or "", reverse=True)[:10]:
            activity.append(
                {
                    "timestamp": run.get("created_at"),
                    "event_type": "workflow_run",
                    "workflow_name": run.get("workflow_name"),
                    "entity_type": "workflow",
                    "entity_id": run.get("workflow_run_id"),
                    "company": None,
                    "contact": None,
                    "owner_or_rep": None,
                    "business_action": f"{human_label(run.get('workflow_name'))} ran",
                    "status": run.get("status"),
                    "human_review_required": bool(run.get("human_review_required")),
                    "sales_manager_label": f"{human_label(run.get('workflow_name'))} ran",
                }
            )
    return activity[:20]


def build_review_queue_health(review_items: list[dict[str, Any]]) -> dict[str, Any]:
    pending = [item for item in review_items if item.get("status") == "pending"]
    return {
        "pending": len(pending),
        "approved": count_where(review_items, "status", "approved"),
        "rejected": count_where(review_items, "status", "rejected"),
        "oldest_pending_review": min(
            (item.get("created_at") for item in pending if item.get("created_at")),
            default=None,
        ),
        "pending_by_workflow": counter_dict(item.get("workflow_name") for item in pending),
        "pending_by_priority": counter_dict(item.get("priority") for item in pending),
        "latest_pending_items": [
            review_summary(item)
            for item in sorted(pending, key=lambda item: item.get("created_at") or "", reverse=True)[:10]
        ],
    }


def build_audit_health(audit_events: list[dict[str, Any]]) -> dict[str, Any]:
    latest = sorted(audit_events, key=lambda item: item.get("created_at") or "", reverse=True)
    return {
        "total_audit_events": len(audit_events),
        "recent_guardrail_events": event_summaries(
            [event for event in latest if event.get("event_type") == "guardrail_triggered"][:10]
        ),
        "recent_blocked_actions": event_summaries(
            [
                event
                for event in latest
                if "blocked" in str(event.get("event_type", "")).lower()
            ][:10]
        ),
        "recent_human_review_required_events": event_summaries(
            [event for event in latest if bool(event.get("human_review_required"))][:10]
        ),
        "latest_audit_events": event_summaries(latest[:10]),
    }


def build_operational_health(step_events: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [event for event in step_events if event.get("step_status") == "failed"]
    latest_failed = sorted(failed, key=lambda item: item.get("created_at") or "", reverse=True)
    return {
        "total_step_events": len(step_events),
        "failed_step_events": len(failed),
        "warning_step_events": sum(
            1
            for event in step_events
            if event.get("severity") == "warning" or event.get("step_status") == "skipped"
        ),
        "retryable_failures": sum(1 for event in failed if bool(event.get("retryable"))),
        "non_retryable_failures": sum(1 for event in failed if not bool(event.get("retryable"))),
        "recent_failed_steps": [step_summary(event) for event in latest_failed[:10]],
        "most_common_error_types": [
            {"error_type": key, "count": count}
            for key, count in Counter(
                event.get("error_type") or "unknown" for event in failed
            ).most_common(8)
        ],
        "recommended_fixes": [
            {"recommended_fix": key, "count": count}
            for key, count in Counter(
                event.get("recommended_fix") for event in failed if event.get("recommended_fix")
            ).most_common(8)
        ],
    }


def build_hubspot_sync_health(records: list[dict[str, Any]]) -> dict[str, Any]:
    latest = sorted(
        records,
        key=lambda item: item.get("last_hubspot_sync_at") or item.get("updated_at") or "",
        reverse=True,
    )
    return {
        "successful_syncs": count_where(records, "hubspot_sync_status", "synced"),
        "partial_syncs": count_where(records, "hubspot_sync_status", "partial_sync"),
        "failed_syncs": count_where(records, "hubspot_sync_status", "failed"),
        "latest_syncs": [lead_summary(record) for record in latest[:10]],
        "records_missing_hubspot_ids": sum(
            1
            for record in records
            if record.get("adapter_mode") == "hubspot"
            and not all(
                [
                    record.get("hubspot_contact_id"),
                    record.get("hubspot_company_id"),
                    record.get("hubspot_deal_id"),
                ]
            )
        ),
        "common_sync_errors": [
            {"error": key, "count": count}
            for key, count in Counter(
                record.get("hubspot_sync_error")
                for record in records
                if record.get("hubspot_sync_error")
            ).most_common(8)
        ],
    }


def build_workflow_health(
    workflow_runs: list[dict[str, Any]], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    runs_by_workflow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in workflow_runs:
        runs_by_workflow[str(run.get("workflow_name"))].append(run)

    health = []
    for workflow_name in sorted(set(runs_by_workflow) | set(AVAILABLE_AI_WORKFLOWS.values())):
        runs = sorted(
            runs_by_workflow.get(workflow_name, []),
            key=lambda item: item.get("created_at") or "",
            reverse=True,
        )
        latest = runs[0] if runs else {}
        partial_count = (
            count_where(records, "hubspot_sync_status", "partial_sync")
            if workflow_name == "hubspot_sync"
            else 0
        )
        health.append(
            {
                "workflow_name": workflow_name,
                "total_runs": len(runs),
                "success_count": count_where(runs, "status", "success"),
                "failure_count": count_where(runs, "status", "failed"),
                "partial_count": partial_count,
                "latest_status": latest.get("status") or "not_enough_data",
                "latest_failure_reason": latest.get("failure_reason"),
                "latest_run_at": latest.get("created_at"),
            }
        )
    return health


def estimate_time_saved_minutes(data: dict[str, list[dict[str, Any]]]) -> int:
    workflow_runs = data["workflow_runs"]
    records = data["crm_records"]
    total = 0
    for run in workflow_runs:
        total += TIME_SAVED_MINUTES.get(str(run.get("workflow_name")), 0)
    total += count_crm_updates_applied(records) * TIME_SAVED_MINUTES["safe_crm_update"]
    total += count_where(records, "hubspot_sync_status", "synced") * TIME_SAVED_MINUTES["hubspot_sync"]
    return total


def used_workflow_keys(
    workflow_runs: list[dict[str, Any]], audit_events: list[dict[str, Any]]
) -> set[str]:
    names = {str(run.get("workflow_name")) for run in workflow_runs}
    names.update(str(event.get("workflow_name")) for event in audit_events)
    used = set()
    for key, workflow_name in AVAILABLE_AI_WORKFLOWS.items():
        if workflow_name in names:
            used.add(key)
    if any("hubspot" in str(event.get("event_type")) for event in audit_events):
        used.add("hubspot_sync")
    return used


def workflow_usage_breakdown(
    workflow_runs: list[dict[str, Any]], audit_events: list[dict[str, Any]]
) -> dict[str, int]:
    counts = Counter()
    for run in workflow_runs:
        counts[str(run.get("workflow_name"))] += 1
    if any("hubspot" in str(event.get("event_type")) for event in audit_events):
        counts["hubspot_sync"] += sum(
            1 for event in audit_events if "hubspot" in str(event.get("event_type"))
        )
    return dict(counts)


def count_recent_failures(step_events: list[dict[str, Any]]) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    count = 0
    for event in step_events:
        if event.get("step_status") != "failed":
            continue
        created_at = parse_datetime(event.get("created_at"))
        if created_at and created_at >= cutoff:
            count += 1
    return count


def count_partial_workflow_runs(records: list[dict[str, Any]]) -> int:
    return count_where(records, "hubspot_sync_status", "partial_sync")


def count_priorities(records: list[dict[str, Any]], priorities: set[str]) -> int:
    return sum(1 for record in records if str(record.get("priority")).lower() in priorities)


def count_crm_updates_applied(records: list[dict[str, Any]]) -> int:
    return sum(
        1
        for record in records
        if record.get("crm_update_status")
        in {"applied", "applied_with_review_visibility"}
    )


def count_where(rows: list[dict[str, Any]], key: str, value: Any) -> int:
    return sum(1 for row in rows if row.get(key) == value)


def count_events(events: list[dict[str, Any]], event_types: set[str]) -> int:
    return sum(1 for event in events if event.get("event_type") in event_types)


def count_distinct_review_required_actions(
    review_items: list[dict[str, Any]], audit_events: list[dict[str, Any]]
) -> int:
    review_item_ids = {
        str(item.get("review_item_id"))
        for item in review_items
        if item.get("review_item_id")
    }
    review_entity_workflows = {
        (str(item.get("entity_id") or ""), str(item.get("workflow_name") or ""))
        for item in review_items
    }
    fallback_action_keys: set[str] = set()

    for event in audit_events:
        if not bool(event.get("human_review_required")):
            continue

        metadata = json_dict(event.get("metadata_json"))
        review_item_id = metadata.get("review_item_id")
        if review_item_id:
            review_item_ids.add(str(review_item_id))
            continue

        entity_id = str(
            event.get("entity_id")
            or metadata.get("crm_record_id")
            or event.get("output_reference")
            or "unknown_entity"
        )
        workflow_name = str(event.get("workflow_name") or "unknown_workflow")
        if (entity_id, workflow_name) in review_entity_workflows:
            continue

        action_type = str(
            metadata.get("business_action")
            or metadata.get("review_type")
            or event.get("event_type")
            or "review_required"
        )
        crm_record_id = str(metadata.get("crm_record_id") or entity_id)
        fallback_action_keys.add(f"{crm_record_id}:{workflow_name}:{action_type}")

    return len(review_item_ids) + len(fallback_action_keys)


def count_risky_records(records: list[dict[str, Any]]) -> int:
    return sum(1 for record in records if record_risk_flags(record))


def count_missing_next_step(records: list[dict[str, Any]]) -> int:
    return sum(1 for record in records if missing_or_unclear(record.get("next_best_action")))


def record_risk_flags(record: dict[str, Any]) -> list[str]:
    return json_list(record.get("risk_flags"))


def json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = decode_json(value, [])
            return decoded if isinstance(decoded, list) else []
        except Exception:
            return []
    return []


def json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = decode_json(value, {})
            return decoded if isinstance(decoded, dict) else {}
        except Exception:
            return {}
    return {}


def missing_or_unclear(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return not normalized or normalized in {"unknown", "none", "not_set"} or "missing" in normalized


def counter_dict(values) -> dict[str, int]:
    return dict(Counter(human_label(value) for value in values if value))


def percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def top_counter_key(counter: dict[str, int]) -> str | None:
    if not counter:
        return None
    return max(counter.items(), key=lambda item: item[1])[0]


def least_counter_key(counter: dict[str, int], available: list[str]) -> str | None:
    if not available:
        return None
    normalized_counter = {key: counter.get(AVAILABLE_AI_WORKFLOWS.get(key, key), 0) for key in available}
    return min(normalized_counter.items(), key=lambda item: item[1])[0]


def latest_timestamp(rows: list[dict[str, Any]]) -> str | None:
    timestamps = [row.get("created_at") for row in rows if row.get("created_at")]
    return max(timestamps) if timestamps else None


def first_value(rows: list[dict[str, Any]], key: str) -> Any:
    for row in rows:
        value = row.get(key)
        if value:
            return value
    return None


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def lead_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "crm_record_id": record.get("crm_record_id"),
        "lead_id": record.get("lead_id"),
        "company": record.get("company"),
        "contact_name": record.get("contact_name"),
        "priority": record.get("priority"),
        "crm_update_status": record.get("crm_update_status"),
        "hubspot_sync_status": record.get("hubspot_sync_status"),
        "next_best_action": record.get("next_best_action"),
        "updated_at": record.get("updated_at"),
    }


def review_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_item_id": item.get("review_item_id"),
        "workflow_name": item.get("workflow_name"),
        "company": item.get("company"),
        "contact_name": item.get("contact_name"),
        "review_type": item.get("review_type"),
        "title": item.get("title"),
        "priority": item.get("priority"),
        "risk_level": item.get("risk_level"),
        "created_at": item.get("created_at"),
    }


def event_summaries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": event.get("event_id"),
            "created_at": event.get("created_at"),
            "event_type": event.get("event_type"),
            "workflow_name": event.get("workflow_name"),
            "entity_type": event.get("entity_type"),
            "entity_id": event.get("entity_id"),
            "human_review_required": bool(event.get("human_review_required")),
            "guardrails_triggered": json_list(event.get("guardrails_triggered")),
            "decision": event.get("decision"),
        }
        for event in events
    ]


def step_summary(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at": event.get("created_at"),
        "workflow_name": event.get("workflow_name"),
        "workflow_run_id": event.get("workflow_run_id"),
        "step_name": event.get("step_name"),
        "step_status": event.get("step_status"),
        "severity": event.get("severity"),
        "error_type": event.get("error_type"),
        "error_message": event.get("error_message"),
        "failure_reason": event.get("failure_reason"),
        "retryable": bool(event.get("retryable")),
        "recommended_fix": event.get("recommended_fix"),
        "entity_type": event.get("entity_type"),
        "entity_id": event.get("entity_id"),
    }


def drop_zone(
    name: str,
    count: int,
    severity: str,
    affected_records: list[Any],
    suggested_manager_action: str,
) -> dict[str, Any]:
    return {
        "zone_name": name,
        "count": count,
        "severity": severity,
        "affected_records": [item for item in affected_records if item][:10],
        "suggested_manager_action": suggested_manager_action,
    }


def unavailable_drop_zone(name: str, reason: str) -> dict[str, Any]:
    return {
        "zone_name": name,
        "count": "not_enough_data",
        "severity": "medium",
        "affected_records": [],
        "suggested_manager_action": reason,
    }


def not_enough_data(reason: str) -> dict[str, str]:
    return {"status": "not_enough_data", "reason": reason}


def sales_manager_label(event_type: str) -> str:
    labels = {
        "lead_scored": "High-priority lead routed",
        "route_recommended": "Lead route recommended",
        "follow_up_draft_created": "Follow-up draft created",
        "proposal_outline_created": "Proposal outline prepared",
        "crm_update_applied": "CRM update applied",
        "crm_update_applied_with_review_visibility": "CRM update applied with review visibility",
        "crm_update_blocked": "CRM update blocked pending review",
        "hubspot_sync_completed": "HubSpot sync completed",
        "hubspot_sync_failed": "HubSpot sync needs attention",
        "hubspot_sync_blocked": "HubSpot sync blocked pending review",
        "crm_hygiene_checked": "Deal hygiene risk checked",
        "meeting_summary_created": "Meeting summary created",
    }
    return labels.get(event_type, "")


def status_from_event(event_type: str) -> str:
    if "blocked" in event_type:
        return "blocked"
    if "failed" in event_type:
        return "failed"
    if "recommended" in event_type:
        return "recommended"
    if "completed" in event_type or "applied" in event_type or "created" in event_type:
        return "applied"
    return "logged"


def human_label(value: Any) -> str:
    text = str(value or "unknown").strip()
    return text.replace("_", " ").replace("-", " ").title()
