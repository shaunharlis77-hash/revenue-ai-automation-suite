import json
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.config.settings import get_settings


def get_database_url() -> str:
    return get_settings().database_url


def get_connection() -> sqlite3.Connection:
    database_url = get_database_url()
    parsed = urlparse(database_url)

    if parsed.scheme != "sqlite":
        raise RuntimeError(
            "Only SQLite is supported by the local database foundation. "
            "Keep workflow services behind this database module for future Postgres support."
        )

    database_path = sqlite_path_from_url(database_url)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    initialize_database(connection)
    return connection


def sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise RuntimeError(f"Unsupported SQLite DATABASE_URL: {database_url}")
    raw_path = database_url.removeprefix(prefix)
    return Path(raw_path)


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS workflow_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_run_id TEXT UNIQUE NOT NULL,
            workflow_name TEXT NOT NULL,
            status TEXT NOT NULL,
            input_reference TEXT,
            output_summary TEXT,
            human_review_required INTEGER NOT NULL DEFAULT 0,
            next_action TEXT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            failed_at TEXT,
            failure_step TEXT,
            failure_reason TEXT,
            created_at TEXT NOT NULL,
            metadata_json TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            workflow_run_id TEXT,
            workflow_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_source TEXT NOT NULL,
            actor TEXT NOT NULL,
            input_reference TEXT,
            output_reference TEXT,
            guardrails_triggered TEXT NOT NULL,
            human_review_required INTEGER NOT NULL DEFAULT 0,
            decision TEXT,
            decision_reason TEXT,
            created_at TEXT NOT NULL,
            metadata_json TEXT
        );

        CREATE TABLE IF NOT EXISTS review_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_item_id TEXT UNIQUE NOT NULL,
            workflow_run_id TEXT,
            workflow_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            company TEXT,
            contact_name TEXT,
            review_type TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            review_reasons TEXT NOT NULL,
            proposed_action TEXT NOT NULL,
            proposed_output TEXT,
            decision TEXT,
            decision_reason TEXT,
            assigned_to TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT
        );

        CREATE TABLE IF NOT EXISTS workflow_step_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            step_event_id TEXT UNIQUE NOT NULL,
            workflow_run_id TEXT NOT NULL,
            workflow_name TEXT NOT NULL,
            step_name TEXT NOT NULL,
            step_status TEXT NOT NULL,
            step_order INTEGER,
            entity_type TEXT,
            entity_id TEXT,
            started_at TEXT,
            completed_at TEXT,
            duration_ms INTEGER,
            severity TEXT NOT NULL,
            error_type TEXT,
            error_message TEXT,
            failure_reason TEXT,
            retryable INTEGER NOT NULL DEFAULT 0,
            recommended_fix TEXT,
            created_at TEXT NOT NULL,
            metadata_json TEXT
        );

        CREATE TABLE IF NOT EXISTS crm_lead_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crm_record_id TEXT UNIQUE NOT NULL,
            lead_id TEXT UNIQUE NOT NULL,
            company TEXT NOT NULL,
            contact_name TEXT,
            email TEXT NOT NULL,
            source TEXT NOT NULL,
            enriched_persona TEXT,
            company_size_band TEXT,
            industry_normalized TEXT,
            region_normalized TEXT,
            lead_score INTEGER NOT NULL,
            priority TEXT NOT NULL,
            confidence TEXT NOT NULL,
            urgency TEXT NOT NULL,
            recommended_route TEXT NOT NULL,
            next_best_action TEXT NOT NULL,
            crm_update_status TEXT NOT NULL,
            human_review_required INTEGER NOT NULL DEFAULT 0,
            risk_flags TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT
        );

        CREATE TABLE IF NOT EXISTS crm_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crm_activity_id TEXT UNIQUE NOT NULL,
            crm_record_id TEXT NOT NULL,
            lead_id TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            activity_title TEXT NOT NULL,
            activity_body TEXT NOT NULL,
            activity_status TEXT NOT NULL,
            source_workflow TEXT NOT NULL,
            workflow_run_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata_json TEXT
        );
        """
    )
    connection.commit()


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def decode_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def reset_persistence_tables() -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM crm_activities")
        connection.execute("DELETE FROM crm_lead_records")
        connection.execute("DELETE FROM workflow_step_events")
        connection.execute("DELETE FROM review_items")
        connection.execute("DELETE FROM audit_events")
        connection.execute("DELETE FROM workflow_runs")
        connection.commit()
