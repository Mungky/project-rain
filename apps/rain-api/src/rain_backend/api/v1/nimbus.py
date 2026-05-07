"""Nimbus — Document Archive Agent (chat-driven flow).

Upload flow:
  1. POST /propose  → validate + name generation, store in memory
  2. POST /confirm/{proposal_id} → create DB record (status=queued), queue for Drive upload
  3. Background worker processes queue one at a time
  4. GET /queue → frontend polls for completion

Pull flow:
  1. GET /search?q= → returns matching docs (blurred for non-admins)
  2. POST /documents/{id}/request-access → email to admin
  3. GET /access/approve/{token} → admin approves, proxies file
  4. GET /access/deny/{token} → admin denies
"""

import asyncio
import io
import logging
import re
import secrets
import smtplib
import time
from datetime import datetime, timedelta, UTC
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rain_backend.api.deps import get_current_user, get_db
from rain_backend.settings import settings
from db.schemas import NimbusDocument, User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["nimbus"])

# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".dwg", ".step", ".stp",
}

FOLDER_CATEGORIES = {"DRW", "QC", "PO", "BA", "PROPOSAL", "INVOICE", "MISC"}

DOC_TYPES = {"PO", "Q", "PL", "QC", "BA", "DRW", "INV", "PROP", "BAST", "MISC"}

# doc_type → default folder_category
DOC_TYPE_FOLDER: dict[str, str] = {
    "PO": "PO", "INV": "INVOICE", "PROP": "PROPOSAL",
    "QC": "QC", "DRW": "DRW", "BA": "BA", "BAST": "BA",
    "Q": "MISC", "PL": "MISC", "MISC": "MISC",
}

# ── In-memory proposal store ──────────────────────────────────────────────────

_proposals: dict[str, dict[str, Any]] = {}
_PROPOSAL_TTL = 30 * 60  # 30 minutes
_queue_lock = asyncio.Lock()
_db_engine = None  # set at startup via init_nimbus_engine()


def init_nimbus_engine(engine) -> None:
    """Called from main.py after DB engine is created."""
    global _db_engine
    _db_engine = engine


def _cleanup_proposals() -> None:
    now = time.time()
    expired = [k for k, v in _proposals.items() if now - v["ts"] > _PROPOSAL_TTL]
    for k in expired:
        del _proposals[k]

# ── Google Drive helpers ──────────────────────────────────────────────────────

def _get_drive_service():
    """Return authenticated Drive service.
    Prefers OAuth2 personal credentials; falls back to service account.
    """
    from googleapiclient.discovery import build  # type: ignore

    # --- OAuth2 personal account (preferred for personal Google/Google One) ---
    if settings.google_oauth_client_id and settings.google_oauth_refresh_token:
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as GoogleRequest
            creds = Credentials(
                token=None,
                refresh_token=settings.google_oauth_refresh_token,
                client_id=settings.google_oauth_client_id,
                client_secret=settings.google_oauth_client_secret,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=["https://www.googleapis.com/auth/drive"],
            )
            creds.refresh(GoogleRequest())
            return build("drive", "v3", credentials=creds, cache_discovery=False)
        except Exception as e:
            logger.warning("OAuth2 Drive auth failed: %s", e)

    # --- Service account fallback ---
    try:
        from google.oauth2 import service_account
        creds_path = settings.google_service_account_json
        if not creds_path or not Path(creds_path).exists():
            return None
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/drive"],
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.warning("Google Drive not available: %s", e)
        return None


def _ensure_folder(service, parent_id: str, folder_name: str) -> str:
    # supportsAllDrives=True required for Shared Drives
    q = (
        f"name='{folder_name}' and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    res = service.files().list(
        q=q, fields="files(id)",
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    return service.files().create(
        body=meta, fields="id", supportsAllDrives=True,
    ).execute()["id"]


def _upload_to_drive(
    service, file_bytes: bytes, filename: str, mime_type: str,
    client_code: str, project_code: str, folder_category: str,
) -> tuple[str, str]:
    from googleapiclient.http import MediaIoBaseUpload  # type: ignore
    root_id = settings.nimbus_drive_root_folder_id
    clients_id = _ensure_folder(service, root_id, "CLIENTS")
    client_id = _ensure_folder(service, clients_id, client_code.upper())
    project_id = _ensure_folder(service, client_id, project_code.upper())
    cat_id = _ensure_folder(service, project_id, folder_category.upper())
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=False)
    file_meta = {"name": filename, "parents": [cat_id]}
    uploaded = service.files().create(
        body=file_meta, media_body=media, fields="id", supportsAllDrives=True,
    ).execute()
    drive_path = (
        f"RAIN-ARCHIVE/CLIENTS/{client_code.upper()}/"
        f"{project_code.upper()}/{folder_category.upper()}/{filename}"
    )
    return uploaded["id"], drive_path

# ── Email notification ────────────────────────────────────────────────────────

def _send_email(subject: str, body_html: str) -> None:
    try:
        gmail_user = settings.gmail_sender
        gmail_pass = settings.gmail_app_password
        if not gmail_user or not gmail_pass:
            logger.warning("Gmail not configured — skipping email")
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
    doc_type: str, seq: int, original_stem: str, suffix: str, version: str = "V1",
) -> str:
    date_str = datetime.now().strftime("%d%m%y")
    clean_stem = re.sub(r"[^\w\-]", "_", original_stem)[:60]
    return f"{doc_type.upper()}-{seq:03d}-{clean_stem}-{date_str}-{version}{suffix}"


async def _next_seq(db: AsyncSession, doc_type: str, client_code: str, project_code: str) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(NimbusDocument.sequence_number), 0) + 1)
        .where(NimbusDocument.doc_type == doc_type)
        .where(NimbusDocument.client_code == client_code.upper())
        .where(NimbusDocument.project_code == project_code.upper())
    )
    return int(result.scalar() or 1)

# ── Background queue processor ────────────────────────────────────────────────

async def _process_doc(doc_id: UUID) -> None:
    """Upload a queued document to Drive. Runs as BackgroundTask."""
    if _db_engine is None:
        logger.error("DB engine not initialised — cannot process queue")
        return

    from sqlalchemy.ext.asyncio import async_sessionmaker
    factory = async_sessionmaker(_db_engine, expire_on_commit=False)

    async with _queue_lock:
        try:
            # Mark processing
            async with factory() as db:
                result = await db.execute(select(NimbusDocument).where(NimbusDocument.id == doc_id))
                doc: NimbusDocument | None = result.scalar_one_or_none()
                if not doc or doc.status != "queued":
                    return
                doc.status = "processing"
                await db.commit()

            # Retrieve file bytes stored in proposal
            proposal = next(
                (p for p in _proposals.values() if p.get("doc_id") == str(doc_id)), None
            )
            file_bytes: bytes | None = proposal.get("file_bytes") if proposal else None

            # Upload + finalise
            async with factory() as db:
                result = await db.execute(select(NimbusDocument).where(NimbusDocument.id == doc_id))
                doc = result.scalar_one_or_none()
                if not doc:
                    return

                archive_status = "archived"
                drive_file_id: str | None = None
                drive_path = doc.drive_path

                if file_bytes:
                    drive_svc = _get_drive_service()
                    if drive_svc:
                        try:
                            drive_file_id, drive_path = _upload_to_drive(
                                drive_svc, file_bytes, doc.archived_filename,
                                proposal.get("mime_type", "application/octet-stream") if proposal else "application/octet-stream",
                                doc.client_code, doc.project_code, doc.folder_category,
                            )
                        except Exception as e:
                            logger.error("Drive upload failed for %s: %s", doc_id, e)
                            archive_status = "failed"
                    else:
                        logger.warning("Drive unavailable — saved to DB only (status=pending)")
                        archive_status = "pending"

                doc.status = archive_status
                doc.drive_file_id = drive_file_id
                doc.drive_path = drive_path
                await db.commit()

                _send_email(
                    subject=f"[Nimbus] {'Archived' if archive_status == 'archived' else 'Gagal'}: {doc.archived_filename}",
                    body_html=f"""
                    <p>Dokumen <b>{doc.archived_filename}</b> telah diproses.</p>
                    <table>
                      <tr><td><b>Status</b></td><td>{archive_status.upper()}</td></tr>
                      <tr><td><b>Client</b></td><td>{doc.client_code}</td></tr>
                      <tr><td><b>Project</b></td><td>{doc.project_code}</td></tr>
                      <tr><td><b>Drive Path</b></td><td>{drive_path}</td></tr>
                    </table>
                    """,
                )

            # Free memory
            if proposal:
                proposal.pop("file_bytes", None)

        except Exception as e:
            logger.error("Queue processor error for %s: %s", doc_id, e)
            try:
                async with factory() as db:
                    result = await db.execute(select(NimbusDocument).where(NimbusDocument.id == doc_id))
                    doc = result.scalar_one_or_none()
                    if doc:
                        doc.status = "failed"
                        await db.commit()
            except Exception:
                pass

# ── Response schemas ──────────────────────────────────────────────────────────

class ProposalResponse(BaseModel):
    proposal_id: str
    proposed_name: str
    original_name: str
    file_size: int
    doc_type: str
    client_code: str
    project_code: str
    folder_category: str
    version: str
    seq_preview: int


class ConfirmRequest(BaseModel):
    doc_type: str
    client_code: str
    project_code: str
    folder_category: str
    version: str = "V1"


class ConfirmResponse(BaseModel):
    doc_id: str
    archived_filename: str
    queue_position: int
    drive_path: str
    message: str


class QueueItem(BaseModel):
    doc_id: str
    archived_filename: str
    status: str
    client_code: str
    project_code: str


class QueueResponse(BaseModel):
    items: list[QueueItem]
    total: int


class SearchResultItem(BaseModel):
    id: str
    archived_filename: str
    doc_type: str
    client_code: str
    project_code: str
    folder_category: str
    status: str
    version: str
    created_at: datetime


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int


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

@router.post("/propose", response_model=ProposalResponse)
async def propose_document(
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[str, Form()] = "MISC",
    client_code: Annotated[str, Form()] = "CLIENT",
    project_code: Annotated[str, Form()] = "PROJECT",
    folder_category: Annotated[str, Form()] = "MISC",
    version: Annotated[str, Form()] = "V1",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProposalResponse:
    """Step 1: Validate file + generate proposed archived name. No Drive upload yet."""
    _cleanup_proposals()

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Tipe file '{suffix}' tidak diizinkan. Gunakan: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    doc_type = doc_type.upper()
    folder_category = folder_category.upper()

    if doc_type not in DOC_TYPES:
        doc_type = "MISC"
    if folder_category not in FOLDER_CATEGORIES:
        folder_category = DOC_TYPE_FOLDER.get(doc_type, "MISC")

    seq = await _next_seq(db, doc_type, client_code, project_code)
    original_stem = Path(file.filename or "document").stem
    proposed_name = _build_archived_name(doc_type, seq, original_stem, suffix, version)

    file_bytes = await file.read()
    proposal_id = str(uuid4())

    _proposals[proposal_id] = {
        "proposal_id": proposal_id,
        "original_filename": file.filename or "unknown",
        "file_bytes": file_bytes,
        "file_size": len(file_bytes),
        "mime_type": file.content_type or "application/octet-stream",
        "suffix": suffix,
        "original_stem": original_stem,
        "doc_type": doc_type,
        "client_code": client_code.upper(),
        "project_code": project_code.upper(),
        "folder_category": folder_category,
        "version": version,
        "seq": seq,
        "proposed_name": proposed_name,
        "user_id": str(current_user.id),
        "username": current_user.username,
        "ts": time.time(),
        "doc_id": None,
    }

    return ProposalResponse(
        proposal_id=proposal_id,
        proposed_name=proposed_name,
        original_name=file.filename or "unknown",
        file_size=len(file_bytes),
        doc_type=doc_type,
        client_code=client_code.upper(),
        project_code=project_code.upper(),
        folder_category=folder_category,
        version=version,
        seq_preview=seq,
    )


@router.post("/confirm/{proposal_id}", response_model=ConfirmResponse)
async def confirm_proposal(
    proposal_id: str,
    body: ConfirmRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfirmResponse:
    """Step 2: User approves proposal. Creates DB record and queues Drive upload."""
    proposal = _proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan atau sudah kadaluarsa (30 menit)")

    # Recalculate with potentially edited metadata
    doc_type = body.doc_type.upper()
    folder_category = body.folder_category.upper()
    client_code = body.client_code.upper()
    project_code = body.project_code.upper()

    seq = await _next_seq(db, doc_type, client_code, project_code)
    archived_filename = _build_archived_name(
        doc_type, seq, proposal["original_stem"], proposal["suffix"], body.version
    )
    drive_path = (
        f"RAIN-ARCHIVE/CLIENTS/{client_code}/{project_code}/{folder_category}/{archived_filename}"
    )

    doc_id = uuid4()
    doc = NimbusDocument(
        id=doc_id,
        original_filename=proposal["original_filename"],
        archived_filename=archived_filename,
        doc_type=doc_type,
        sequence_number=seq,
        client_code=client_code,
        project_code=project_code,
        folder_category=folder_category,
        drive_file_id=None,
        drive_path=drive_path,
        status="queued",
        version=body.version,
        uploaded_by_user_id=current_user.id,
        uploaded_by_name=current_user.username,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Link proposal to doc_id so background task can find file bytes
    proposal["doc_id"] = str(doc_id)
    proposal["doc_type"] = doc_type
    proposal["client_code"] = client_code
    proposal["project_code"] = project_code
    proposal["folder_category"] = folder_category
    proposal["version"] = body.version

    # Count queue position
    queue_result = await db.execute(
        select(func.count()).where(NimbusDocument.status.in_(["queued", "processing"]))
    )
    queue_pos = int(queue_result.scalar() or 1)

    # Kick off background upload
    background_tasks.add_task(_process_doc, doc_id)

    return ConfirmResponse(
        doc_id=str(doc_id),
        archived_filename=archived_filename,
        queue_position=queue_pos,
        drive_path=drive_path,
        message=f"Ditambahkan ke queue (posisi {queue_pos}). Saya kabarin kalau sudah selesai.",
    )


@router.get("/queue", response_model=QueueResponse)
async def get_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueResponse:
    """Get current upload queue (queued + processing documents)."""
    stmt = (
        select(NimbusDocument)
        .where(NimbusDocument.status.in_(["queued", "processing"]))
        .order_by(NimbusDocument.created_at.asc())
    )
    if current_user.role != "admin":
        stmt = stmt.where(NimbusDocument.uploaded_by_user_id == current_user.id)

    result = await db.execute(stmt)
    docs = result.scalars().all()
    items = [
        QueueItem(
            doc_id=str(d.id),
            archived_filename=d.archived_filename,
            status=d.status,
            client_code=d.client_code,
            project_code=d.project_code,
        )
        for d in docs
    ]
    return QueueResponse(items=items, total=len(items))


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search archived documents by text (client, project, filename)."""
    if not q.strip():
        return SearchResponse(results=[], total=0)

    pattern = f"%{q.strip()}%"
    stmt = (
        select(NimbusDocument)
        .where(
            NimbusDocument.status.in_(["archived", "pending", "failed"]),
        )
        .where(
            or_(
                NimbusDocument.client_code.ilike(pattern),
                NimbusDocument.project_code.ilike(pattern),
                NimbusDocument.archived_filename.ilike(pattern),
                NimbusDocument.doc_type.ilike(pattern),
            )
        )
        .order_by(NimbusDocument.created_at.desc())
        .limit(10)
    )
    if current_user.role != "admin":
        stmt = stmt.where(NimbusDocument.uploaded_by_user_id == current_user.id)

    result = await db.execute(stmt)
    docs = result.scalars().all()
    items = [
        SearchResultItem(
            id=str(d.id),
            archived_filename=d.archived_filename,
            doc_type=d.doc_type,
            client_code=d.client_code,
            project_code=d.project_code,
            folder_category=d.folder_category,
            status=d.status,
            version=d.version,
            created_at=d.created_at,
        )
        for d in docs
    ]
    return SearchResponse(results=items, total=len(items))


@router.get("/documents", response_model=NimbusDocListResponse)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NimbusDocListResponse:
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
    result = await db.execute(select(NimbusDocument).where(NimbusDocument.id == doc_id))
    doc: NimbusDocument | None = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

    token = secrets.token_hex(32)
    doc.access_token = token
    doc.access_token_expires_at = datetime.now(UTC) + timedelta(minutes=15)
    doc.status = "access_requested"
    await db.commit()

    approve_url = f"{settings.backend_origin}/v1/nimbus/access/approve/{token}"
    deny_url = f"{settings.backend_origin}/v1/nimbus/access/deny/{token}"

    _send_email(
        subject=f"[Rain] Permintaan Akses: {doc.archived_filename}",
        body_html=f"""
        <p><b>{current_user.username}</b> ingin mengakses:</p>
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
        <p style="color:#888;font-size:12px">Link approval berlaku 15 menit.</p>
        """,
    )

    return {
        "doc_id": str(doc_id),
        "message": "Permintaan terkirim. Menunggu approval...",
    }


@router.get("/access/approve/{token}")
async def approve_access(token: str, db: AsyncSession = Depends(get_db)):
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
        raise HTTPException(status_code=410, detail="Link sudah kadaluarsa")

    doc.status = "access_approved"
    await db.commit()

    drive_svc = _get_drive_service()
    if not drive_svc or not doc.drive_file_id:
        raise HTTPException(status_code=503, detail="Drive tidak tersedia")

    from googleapiclient.http import MediaIoBaseDownload  # type: ignore

    request = drive_svc.files().get_media(fileId=doc.drive_file_id, supportsAllDrives=True)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)

    def _stream():
        while chunk := buf.read(65536):
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{doc.archived_filename}"'},
    )


@router.get("/access/deny/{token}")
async def deny_access(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NimbusDocument).where(NimbusDocument.access_token == token)
    )
    doc: NimbusDocument | None = result.scalar_one_or_none()
    if doc:
        doc.status = "access_denied"
        doc.access_token = None
        await db.commit()
    return {"message": "Akses ditolak."}
