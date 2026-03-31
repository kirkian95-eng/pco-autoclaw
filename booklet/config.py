from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_FILE = REPO_ROOT / "config.env"


@dataclass(frozen=True)
class BookletConfig:
    repo_root: Path
    data_dir: Path
    manifest_db: Path
    default_service_type_id: str
    planning_workbook_file: Path
    google_service_account_file: Path | None
    google_template_root_id: str | None
    google_output_root_id: str | None
    ordinary_template_doc_id: str | None
    google_oauth_client_secret_file: Path | None
    google_oauth_token_file: Path | None
    google_oauth_session_file: Path
    esv_api_token: str | None

    def missing_for_generation(self) -> list[str]:
        missing: list[str] = []
        if not self.google_service_account_file:
            missing.append("GOOGLE_SERVICE_ACCOUNT_FILE")
        if not self.google_template_root_id:
            missing.append("BOOKLET_GOOGLE_TEMPLATE_ROOT_ID")
        if not self.google_output_root_id:
            missing.append("BOOKLET_GOOGLE_OUTPUT_ROOT_ID")
        if not self.esv_api_token:
            missing.append("ESV_API_TOKEN")
        return missing


def load_config() -> BookletConfig:
    if DEFAULT_CONFIG_FILE.exists():
        load_dotenv(DEFAULT_CONFIG_FILE)

    data_dir = REPO_ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    manifest_db = Path(
        os.getenv(
            "BOOKLET_MANIFEST_DB",
            str(data_dir / "booklet_manifest.sqlite3"),
        )
    )
    planning_workbook_file = Path(
        os.getenv(
            "BOOKLET_PLANNING_WORKBOOK",
            str(data_dir / "2026-planning-worksheet.xlsx"),
        )
    )

    google_service_account = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    google_oauth_client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_FILE")
    google_oauth_token = os.getenv("GOOGLE_OAUTH_TOKEN_FILE")
    google_oauth_session = os.getenv(
        "GOOGLE_OAUTH_SESSION_FILE",
        str(data_dir / "google-oauth-session.json"),
    )

    return BookletConfig(
        repo_root=REPO_ROOT,
        data_dir=data_dir,
        manifest_db=manifest_db,
        default_service_type_id=os.getenv("BOOKLET_SERVICE_TYPE_ID", ""),
        planning_workbook_file=planning_workbook_file,
        google_service_account_file=Path(google_service_account)
        if google_service_account
        else None,
        google_template_root_id=os.getenv("BOOKLET_GOOGLE_TEMPLATE_ROOT_ID"),
        google_output_root_id=os.getenv("BOOKLET_GOOGLE_OUTPUT_ROOT_ID"),
        ordinary_template_doc_id=os.getenv("BOOKLET_ORDINARY_TEMPLATE_DOC_ID"),
        google_oauth_client_secret_file=Path(google_oauth_client_secret)
        if google_oauth_client_secret
        else None,
        google_oauth_token_file=Path(google_oauth_token)
        if google_oauth_token
        else None,
        google_oauth_session_file=Path(google_oauth_session),
        esv_api_token=os.getenv("ESV_API_TOKEN"),
    )
