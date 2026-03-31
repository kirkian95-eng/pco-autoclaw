from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import PlannedService


def init_manifest(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS booklet_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_date TEXT NOT NULL,
                service_type_id TEXT NOT NULL,
                template_family TEXT NOT NULL,
                season TEXT NOT NULL,
                observance TEXT,
                plan_id TEXT,
                doc_id TEXT,
                status TEXT NOT NULL DEFAULT 'planned',
                source_snapshot_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(service_date, service_type_id)
            );

            CREATE TABLE IF NOT EXISTS booklet_managed_sections (
                document_id INTEGER NOT NULL REFERENCES booklet_documents(id) ON DELETE CASCADE,
                section_key TEXT NOT NULL,
                rendered_hash TEXT,
                source_hash TEXT,
                sync_state TEXT NOT NULL DEFAULT 'pending',
                updated_at TEXT NOT NULL,
                PRIMARY KEY(document_id, section_key)
            );
            """
        )


def upsert_planned_service(db_path: Path, planned: PlannedService) -> int:
    now = _utc_now()
    payload = json.dumps(asdict(planned), sort_keys=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.execute(
            """
            INSERT INTO booklet_documents (
                service_date,
                service_type_id,
                template_family,
                season,
                observance,
                plan_id,
                doc_id,
                status,
                source_snapshot_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?, ?)
            ON CONFLICT(service_date, service_type_id) DO UPDATE SET
                template_family = excluded.template_family,
                season = excluded.season,
                observance = excluded.observance,
                source_snapshot_json = excluded.source_snapshot_json,
                updated_at = excluded.updated_at
            """,
            (
                planned.service_date,
                planned.service_type_id,
                planned.template_family,
                planned.season,
                planned.observance,
                planned.plan_id,
                planned.doc_id,
                payload,
                now,
                now,
            ),
        )
        if cur.lastrowid:
            return int(cur.lastrowid)
        row = conn.execute(
            """
            SELECT id
            FROM booklet_documents
            WHERE service_date = ? AND service_type_id = ?
            """,
            (planned.service_date, planned.service_type_id),
        ).fetchone()
        return int(row[0])


def list_planned_services(db_path: Path) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, service_date, service_type_id, template_family, season,
                   observance, plan_id, doc_id, status, updated_at
            FROM booklet_documents
            ORDER BY service_date ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_planned_service(
    db_path: Path,
    service_date: str,
    service_type_id: str,
) -> dict | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, service_date, service_type_id, template_family, season,
                   observance, plan_id, doc_id, status, source_snapshot_json, updated_at
            FROM booklet_documents
            WHERE service_date = ? AND service_type_id = ?
            """,
            (service_date, service_type_id),
        ).fetchone()
    return dict(row) if row else None


def mark_generated_service(
    db_path: Path,
    service_date: str,
    service_type_id: str,
    doc_id: str,
    source_snapshot: dict,
) -> None:
    now = _utc_now()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            UPDATE booklet_documents
            SET doc_id = ?,
                status = 'generated',
                source_snapshot_json = ?,
                updated_at = ?
            WHERE service_date = ? AND service_type_id = ?
            """,
            (
                doc_id,
                json.dumps(source_snapshot, sort_keys=True),
                now,
                service_date,
                service_type_id,
            ),
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
