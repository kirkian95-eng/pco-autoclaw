from __future__ import annotations

import json
import re
import tempfile
from datetime import date
from pathlib import Path

from booklet.config import BookletConfig
from booklet.manifest import get_planned_service
from booklet.sources.google_docs import GoogleDocsClient
from booklet.sources.pco_services import PlanningCenterSource
from pco_client import PCOClient


def attach_booklet_pdf(
    config: BookletConfig,
    service_date: str,
    service_type_id: str,
    doc_id: str | None = None,
    plan_id: str | None = None,
    filename: str | None = None,
) -> dict:
    existing = get_planned_service(
        config.manifest_db,
        service_date=service_date,
        service_type_id=service_type_id,
    )
    if not existing and not doc_id:
        raise ValueError("No generated booklet exists for that Sunday.")

    resolved_doc_id = doc_id or existing.get("doc_id")
    if not resolved_doc_id:
        raise ValueError("No generated Google Doc is recorded for that Sunday.")

    resolved_plan_id = plan_id or _extract_plan_id(existing)
    if not resolved_plan_id:
        resolved_plan_id = _resolve_plan_id_for_date(service_type_id, service_date)
    if not resolved_plan_id:
        raise ValueError("No Planning Center plan ID is recorded for that Sunday.")

    docs_client = GoogleDocsClient(config)
    doc_title = docs_client.get_doc_title(resolved_doc_id)
    attachment_name = filename or build_pdf_filename(doc_title, service_date)

    with tempfile.TemporaryDirectory(prefix="booklet-pdf-") as tmp_dir:
        pdf_path = Path(tmp_dir) / attachment_name
        docs_client.export_doc_pdf(resolved_doc_id, pdf_path)

        pco = PCOClient()
        attachment = pco.replace_plan_attachment(
            service_type_id=service_type_id,
            plan_id=resolved_plan_id,
            file_path=pdf_path,
            filename=attachment_name,
        )

    attrs = attachment.get("attributes") or {}
    return {
        "attachment_id": attachment["id"],
        "attachment_name": attrs.get("filename") or attrs.get("display_name") or attachment_name,
        "attachment_url": attrs.get("url"),
        "doc_id": resolved_doc_id,
        "plan_id": resolved_plan_id,
        "service_date": service_date,
        "status": "attached_pdf",
    }


def build_pdf_filename(doc_title: str, service_date: str) -> str:
    base = doc_title.strip() or f"Sunday Morning Liturgy {service_date}"
    clean = re.sub(r"[^A-Za-z0-9._ -]+", "", base)
    clean = re.sub(r"\s+", " ", clean).strip().rstrip(".")
    if not clean.lower().endswith(".pdf"):
        clean = f"{clean}.pdf"
    return clean


def _extract_plan_id(existing: dict | None) -> str | None:
    if not existing:
        return None
    if existing.get("plan_id"):
        return existing["plan_id"]
    raw = existing.get("source_snapshot_json")
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload.get("plan_id")


def _resolve_plan_id_for_date(service_type_id: str, service_date: str) -> str | None:
    source = PlanningCenterSource()
    plan = source.get_plan_for_date(service_type_id, date.fromisoformat(service_date))
    if not plan:
        return None
    return plan.get("id")
