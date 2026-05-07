"""Nimbus — Document Archive Agent.

Flow:
  1. User uploads file → POST /v1/nimbus/upload
     - Validates file type
     - Builds archived filename (Jenis-NomorUrut-NamaFile-DDMMYY-Version)
     - Uploads to Google Drive folder
     - Saves record to DB
     - Sends email notification to admin

  2. Admin views all documents via DCC → GET /v1/nimbus/documents

  3. User requests access → POST /v1/nimbus/documents/{id}/request-access
     - Creates 15-min expiry token
     - Sends email to admin with approve URL

  4. Admin approves → GET /v1/nimbus/access/approve/{token}
     - Marks approved, returns a short-lived redirect URL that proxies the file
     (Rain serves the file from Drive — user never gets a raw Drive link)
"""

import io
import logging
import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta, UTC
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rain_backend.api.deps import get_current_user, get_db
from rain_backend.settings import settings
from db.schemas import NimbusDocument, User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["nimbus"])

# ── Allowed file types ────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".dwg", ".step", ".stp",
}

FOLDER_CATEGORIES = {"DRW", "QC", "PO", "BA", "PROPOSAL", "INVOICE", "MISC"}

DOC_TYPES = {
    "PO", "Q", "PL", "QC", "BA", "DRW", "INV", "PROP", "BAST", "MISC",
}

# ── Google Drive helpers ──────────────────────────────────────────────────────

def _get_drive_service():
    """Return an authenticated Google Drive service, or None if not configured."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build  # type: ignore

        creds_path = settings.google_service_account_json
        if not creds_path or not Path(creds_path).exists():
            return None
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.warning("Google Drive not available: %s", e)
        return None


def _ensure_folder(service, parent_id: str, folder_name: str) -> str:
    """Get or create a subfolder. Returns folder ID."""
    q = (
        f"name='{folder_name}' and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    res = service.files().list(q=q, fields="files(id)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def _upload_to_drive(
    service,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    client_code: str,
    project_code: str,
    folder_category: str,
) -> tuple[str, str]:
    """
    Upload file into RAIN-ARCHIVE/CLIENTS/{client}/{project}/{category}/.
    Returns (file_id, drive_path).
    """
    from googleapiclient.http import MediaIoBaseUpload  # type: ignore

    root_id = settings.nimbus_drive_root_folder_id
    clients_id = _ensure_folder(service, root_id, "CLIENTS")
    client_id = _ensure_folder(service, clients_id, client_code.upper())
    project_id = _ensure_folder(service, client_id, project_code.upper())
    cat_id = _ensure_folder(service, project_id, folder_category.upper())

    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=False)
    file_meta = {"name": filename, "parents": [cat_id]}
    uploaded = service.files().create(body=file_meta, media_body=media, fields="id").execute()
    drive_path = f"RAIN-ARCHIVE/CLIENTS/{client_code.upper()}/{project_code.upper()}/{folder_category.upper()}/{filename}"
    return uploaded["id"], drive_path


# ── Email notification ────────────────────────────────────────────────────────

def _send_email(subject: str, body_html: str) -> None:
    """Send email via Gmail SMTP using app password."""
    try:
        gmail_user = settings.gmail_sender
        gmail_pass = settings.gmail_app_password
        if not gmail_user or not gmail_pass:
            logger.warning("Gmail not configured — skipping email notification")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = settings.admin_email or gmail_user
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, msg["To"], msg.as_string())
        logger.info("Email sent: %s", subject)
    except Exception as e:
        logger.error("Email send failed: %s", e)


# ── Naming helper ─────────────────────────────────────────────────────────────

def _build_archived_name(
    doc_type: str,
    seq: int,
    original_stem: str,
    suffix: str,
    version: str = "V1",
) -> str:
    date_str = datetime.now().strftime("%d%m%y")
    clean_stem = re.sub(r"[^\w\-]", "_", original_stem)[:60]
    return f"{doc_type.upper()}-{seq:03d}-{clean_stem}-{date_str}-{version}{suffix}"


# ── Request / Response schemas ────────────────────────────────────────────────

class NimbusDocOut(BaseModel):
    id: UUID
    original_filename: str
    archived_filename: str
    doc_type: str
    client_code: str
    project_code: str
    folder_category: str
    drive_path: str
    drive_file_id: str | None
    status: str
    uploaded_by: str
    version: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NimbusDocListResponse(BaseModel):
    documents: list[NimbusDocOut]
    total: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=NimbusDocOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[str, Form()],
    client_code: Annotated[str, Form()],
    project_code: Annotated[str, Form()],
    folder_category: Annotated[str, Form()],
    version: Annotated[str, Form()] = "V1",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NimbusDocOut:
    """Upload a document. Nimbus renames it and archives to Google Drive."""
    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Tipe file '{suffix}' tidak diizinkan. Gunakan: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    doc_type = doc_type.upper()
    folder_category = folder_category.upper()

    if doc_type not in DOC_TYPES:
        raise HTTPException(status_code=422, detail=f"doc_type harus salah satu dari: {', '.join(DOC_TYPES)}")
    if folder_category not in FOLDER_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"folder_category harus salah satu dari: {', '.join(FOLDER_CATEGORIES)}")

    # Auto-increment sequence
    seq_result = await db.execute(
        select(func.coalesce(func.max(NimbusDocument.sequence_number), 0) + 1)
        .where(NimbusDocument.doc_type == doc_type)
        .where(NimbusDocument.client_code == client_code.upper())
        .where(NimbusDocument.project_code == project_code.upper())
    )
    seq = int(seq_result.scalar() or 1)

    original_stem = Path(file.filename or "document").stem
    archived_filename = _build_archived_name(doc_type, seq, original_stem, suffix, version)

    file_bytes = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    # Upload to Google Drive
    drive_file_id: str | None = None
    drive_path = f"RAIN-ARCHIVE/CLIENTS/{client_code.upper()}/{project_code.upper()}/{folder_category.upper()}/{archived_filename}"
    archive_status = "archived"

    drive_svc = _get_drive_service()
    if drive_svc:
        try:
            drive_file_id, drive_path = _upload_to_drive(
                drive_svc, file_bytes, archived_filename, mime_type,
                client_code, project_code, folder_category,
            )
        except Exception as e:
            logger.error("Drive upload failed: %s", e)
            archive_status = "failed"
    else:
        logger.warning("Drive service unavailable — document saved to DB only")
        archive_status = "pending"

    doc = NimbusDocument(
        original_filename=file.filename or "unknown",
        archived_filename=archived_filename,
        doc_type=doc_type,
        sequence_number=seq,
        client_code=client_code.upper(),
        project_code=project_code.upper(),
        folder_category=folder_category,
        drive_file_id=drive_file_id,
        drive_path=drive_path,
        status=archive_status,
        version=version,
        uploaded_by_user_id=current_user.id,
        uploaded_by_name=current_user.username,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Email notification to admin
    _send_email(
        subject=f"[Rain] Dokumen baru: {archived_filename}",
        body_html=f"""
        <p>Dokumen baru telah diarsipkan oleh <b>{current_user.username}</b>.</p>
        <table>
          <tr><td><b>File Asli</b></td><td>{file.filename}</td></tr>
          <tr><td><b>Nama Arsip</b></td><td>{archived_filename}</td></tr>
          <tr><td><b>Client</b></td><td>{client_code.upper()}</td></tr>
          <tr><td><b>Project</b></td><td>{project_code.upper()}</td></tr>
          <tr><td><b>Folder</b></td><td>{folder_category}</td></tr>
          <tr><td><b>Status</b></td><td>{archive_status}</td></tr>
          <tr><td><b>Drive Path</b></td><td>{drive_path}</td></tr>
        </table>
        """,
    )

    return NimbusDocOut(
        id=doc.id,
        original_filename=doc.original_filename,
        archived_filename=doc.archived_filename,
        doc_type=doc.doc_type,
        client_code=doc.client_code,
        project_code=doc.project_code,
        folder_category=doc.folder_category,
        drive_path=doc.drive_path,
        drive_file_id=doc.drive_file_id,
        status=doc.status,
        uploaded_by=doc.uploaded_by_name or "unknown",
        version=doc.version,
        created_at=doc.created_at,
    )


@router.get("/documents", response_model=NimbusDocListResponse)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NimbusDocListResponse:
    """List all archived documents (admin sees all; user sees their own)."""
    stmt = select(NimbusDocument).order_by(NimbusDocument.created_at.desc())
    if current_user.role != "admin":
        stmt = stmt.where(NimbusDocument.uploaded_by_user_id == current_user.id)

    result = await db.execute(stmt)
    docs = result.scalars().all()
    out = [
        NimbusDocOut(
            id=d.id,
            original_filename=d.original_filename,
            archived_filename=d.archived_filename,
            doc_type=d.doc_type,
            client_code=d.client_code,
            project_code=d.project_code,
            folder_category=d.folder_category,
            drive_path=d.drive_path,
            drive_file_id=d.drive_file_id,
            status=d.status,
            uploaded_by=d.uploaded_by_name or "unknown",
            version=d.version,
            created_at=d.created_at,
        )
        for d in docs
    ]
    return NimbusDocListResponse(documents=out, total=len(out))


@router.post("/documents/{doc_id}/request-access")
async def request_access(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """User requests access to download a specific document.
    Sends approval email to admin. Admin must approve before a link is issued.
    """
    result = await db.execute(select(NimbusDocument).where(NimbusDocument.id == doc_id))
    doc: NimbusDocument | None = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    token = secrets.token_hex(32)
    doc.access_token = token
    doc.access_token_expires_at = datetime.now(UTC) + timedelta(minutes=15)
    doc.status = "access_requested"
    await db.commit()

    base_url = settings.frontend_origin
    approve_url = f"{settings.backend_origin}/v1/nimbus/access/approve/{token}"
    deny_url = f"{settings.backend_origin}/v1/nimbus/access/deny/{token}"

    _send_email(
        subject=f"[Rain] Permintaan Akses: {doc.archived_filename}",
        body_html=f"""
        <p><b>{current_user.username}</b> ingin mengakses dokumen:</p>
        <p><b>{doc.archived_filename}</b> ({doc.client_code}/{doc.project_code})</p>
        <br>
        <p>
          <a href="{approve_url}" style="background:#16a34a;color:white;padding:8px 16px;border-radius:4px;text-decoration:none">
            ✅ Approve
          </a>
          &nbsp;&nbsp;
          <a href="{deny_url}" style="background:#dc2626;color:white;padding:8px 16px;border-radius:4px;text-decoration:none">
            ❌ Deny
          </a>
        </p>
        <p style="color:#888;font-size:12px">Link berlaku 15 menit.</p>
        """,
    )

    return {"message": "Permintaan akses terkirim. Menunggu persetujuan."}


@router.get("/access/approve/{token}")
async def approve_access(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Admin clicks approve link from email. Returns a proxied file stream."""
    result = await db.execute(
        select(NimbusDocument).where(NimbusDocument.access_token == token)
    )
    doc: NimbusDocument | None = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Token tidak valid")

    now = datetime.now(UTC)
    if doc.access_token_expires_at and doc.access_token_expires_at < now:
        doc.status = "archived"
        doc.access_token = None
        await db.commit()
        raise HTTPException(status_code=410, detail="Link sudah kadaluarsa (15 menit)")

    doc.status = "access_approved"
    await db.commit()

    # Proxy download from Drive
    drive_svc = _get_drive_service()
    if not drive_svc or not doc.drive_file_id:
        raise HTTPException(status_code=503, detail="Drive tidak tersedia saat ini")

    from googleapiclient.http import MediaIoBaseDownload  # type: ignore
    from fastapi.responses import StreamingResponse

    request = drive_svc.files().get_media(fileId=doc.drive_file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)

    def _stream():
        while True:
            chunk = buf.read(65536)
            if not chunk:
                break
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{doc.archived_filename}"'},
    )


@router.get("/access/deny/{token}")
async def deny_access(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Admin clicks deny link from email."""
    result = await db.execute(
        select(NimbusDocument).where(NimbusDocument.access_token == token)
    )
    doc: NimbusDocument | None = result.scalar_one_or_none()
    if doc:
        doc.status = "access_denied"
        doc.access_token = None
        await db.commit()
    return {"message": "Akses ditolak."}
