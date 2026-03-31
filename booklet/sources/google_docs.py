from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow

from booklet.config import BookletConfig


GOOGLE_DRIVE_RW = "https://www.googleapis.com/auth/drive"
GOOGLE_DOCS_RW = "https://www.googleapis.com/auth/documents"


@dataclass
class CopiedDoc:
    doc_id: str
    title: str
    parent_id: str | None


@dataclass
class DocumentParagraph:
    start_index: int
    end_index: int
    text: str
    style: str
    alignment: str | None

    @property
    def content_end_index(self) -> int:
        return self.end_index - 1


@dataclass(frozen=True)
class TextReplacement:
    start_index: int
    end_index: int
    text: str
    description: str


class GoogleDocsClient:
    def __init__(self, config: BookletConfig):
        creds = load_google_credentials(config)
        self.drive = build("drive", "v3", credentials=creds)
        self.docs = build("docs", "v1", credentials=creds)

    def get_document(self, doc_id: str) -> dict:
        return self.docs.documents().get(documentId=doc_id).execute()

    def get_paragraphs(self, doc_id: str) -> list[DocumentParagraph]:
        return extract_document_paragraphs(self.get_document(doc_id))

    def get_doc_title(self, doc_id: str) -> str:
        doc = self.get_document(doc_id)
        return doc.get("title", "")

    def copy_doc(self, source_doc_id: str, new_title: str, parent_folder_id: str) -> CopiedDoc:
        body = {
            "name": new_title,
            "parents": [parent_folder_id],
        }
        new_file = self.drive.files().copy(
            fileId=source_doc_id,
            body=body,
            supportsAllDrives=True,
            fields="id,name,parents",
        ).execute()
        parents = new_file.get("parents") or []
        return CopiedDoc(
            doc_id=new_file["id"],
            title=new_file["name"],
            parent_id=parents[0] if parents else None,
        )

    def export_doc_pdf(self, doc_id: str, output_path: Path) -> Path:
        request = self.drive.files().export_media(
            fileId=doc_id,
            mimeType="application/pdf",
        )
        buffer = BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        output_path.write_bytes(buffer.getvalue())
        return output_path

    def apply_text_replacements(
        self,
        doc_id: str,
        replacements: list[TextReplacement],
    ) -> dict | None:
        if not replacements:
            return None
        requests = []
        for replacement in sorted(replacements, key=lambda item: item.start_index, reverse=True):
            requests.append(
                {
                    "deleteContentRange": {
                        "range": {
                            "startIndex": replacement.start_index,
                            "endIndex": replacement.end_index,
                        }
                    }
                }
            )
            if replacement.text:
                requests.append(
                    {
                        "insertText": {
                            "location": {"index": replacement.start_index},
                            "text": replacement.text,
                        }
                    }
                )
        return self.docs.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()


def load_google_credentials(config: BookletConfig):
    scopes = [GOOGLE_DRIVE_RW, GOOGLE_DOCS_RW]

    if config.google_oauth_token_file and config.google_oauth_token_file.exists():
        creds = Credentials.from_authorized_user_file(
            str(config.google_oauth_token_file),
            scopes=scopes,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            config.google_oauth_token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if config.google_service_account_file:
        return service_account.Credentials.from_service_account_file(
            str(config.google_service_account_file),
            scopes=scopes,
        )

    raise ValueError(
        "Google credentials not configured. Provide OAuth token or service account."
    )


def start_oauth_console_flow(config: BookletConfig) -> tuple[str, str]:
    if not config.google_oauth_client_secret_file:
        raise ValueError("GOOGLE_OAUTH_CLIENT_SECRET_FILE is required")

    scopes = [GOOGLE_DRIVE_RW, GOOGLE_DOCS_RW]
    flow = InstalledAppFlow.from_client_secrets_file(
        str(config.google_oauth_client_secret_file),
        scopes=scopes,
    )
    flow.redirect_uri = _default_oauth_redirect_uri(config)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    _write_oauth_session(
        config,
        {
            "state": state,
            "code_verifier": flow.code_verifier,
            "redirect_uri": flow.redirect_uri,
        },
    )
    return auth_url, state


def finish_oauth_console_flow(
    config: BookletConfig,
    auth_code: str | None,
    state: str | None,
    response_url: str | None = None,
) -> Path:
    if not config.google_oauth_client_secret_file:
        raise ValueError("GOOGLE_OAUTH_CLIENT_SECRET_FILE is required")
    if not config.google_oauth_token_file:
        raise ValueError("GOOGLE_OAUTH_TOKEN_FILE is required")

    scopes = [GOOGLE_DRIVE_RW, GOOGLE_DOCS_RW]
    session_payload = _read_oauth_session(config)
    resolved_state = state or session_payload.get("state")
    flow = InstalledAppFlow.from_client_secrets_file(
        str(config.google_oauth_client_secret_file),
        scopes=scopes,
        state=resolved_state,
    )
    flow.redirect_uri = session_payload.get("redirect_uri") or _default_oauth_redirect_uri(config)
    flow.code_verifier = session_payload.get("code_verifier")
    if flow.redirect_uri.startswith("http://localhost"):
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    if response_url:
        flow.fetch_token(authorization_response=response_url)
    elif auth_code:
        flow.fetch_token(code=auth_code)
    else:
        raise ValueError("Provide either an authorization code or a response URL")
    config.google_oauth_token_file.write_text(
        flow.credentials.to_json(),
        encoding="utf-8",
    )
    if config.google_oauth_session_file.exists():
        config.google_oauth_session_file.unlink()
    return config.google_oauth_token_file


def _default_oauth_redirect_uri(config: BookletConfig) -> str:
    payload = _load_oauth_client_payload(config)
    redirect_uris = payload.get("installed", {}).get("redirect_uris") or []
    if not redirect_uris:
        raise ValueError("No redirect URIs found in GOOGLE_OAUTH_CLIENT_SECRET_FILE")
    return redirect_uris[0]


def _load_oauth_client_payload(config: BookletConfig) -> dict:
    if not config.google_oauth_client_secret_file:
        raise ValueError("GOOGLE_OAUTH_CLIENT_SECRET_FILE is required")
    return json.loads(config.google_oauth_client_secret_file.read_text(encoding="utf-8"))


def _write_oauth_session(config: BookletConfig, payload: dict) -> None:
    config.google_oauth_session_file.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _read_oauth_session(config: BookletConfig) -> dict:
    if not config.google_oauth_session_file.exists():
        raise ValueError("No pending Google OAuth session found. Run auth-google first.")
    return json.loads(config.google_oauth_session_file.read_text(encoding="utf-8"))


def extract_document_paragraphs(document: dict) -> list[DocumentParagraph]:
    paragraphs: list[DocumentParagraph] = []
    for element in document.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        text = "".join(
            run.get("textRun", {}).get("content", "") for run in paragraph.get("elements", [])
        ).strip("\n")
        if not text.strip():
            continue
        paragraph_style = paragraph.get("paragraphStyle", {})
        paragraphs.append(
            DocumentParagraph(
                start_index=element["startIndex"],
                end_index=element["endIndex"],
                text=" ".join(text.split()),
                style=paragraph_style.get("namedStyleType", "NORMAL_TEXT"),
                alignment=paragraph_style.get("alignment"),
            )
        )
    return paragraphs
