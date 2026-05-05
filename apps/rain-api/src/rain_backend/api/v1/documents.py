"""Document upload endpoints."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from rain_backend.api.deps import get_db, get_minio, get_qdrant, get_providers
from db.schemas.dto_document import DocumentUploadResponse, DocumentListResponse, DocumentResponse
from rain_brain.services.document_service import DocumentService, ALLOWED_MIMES

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List all uploaded documents."""
    service = DocumentService(db)
    docs, total = await service.list_documents(limit=limit, offset=offset)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total_count=total,
    )


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    minio_client=Depends(get_minio),
    qdrant_client=Depends(get_qdrant),
    providers: dict = Depends(get_providers),
) -> DocumentUploadResponse:
    """Upload and process a document for RAG."""
    # Check infrastructure availability
    if minio_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "minio_unavailable", "message": "MinIO storage is not available"},
        )
    if qdrant_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "qdrant_unavailable", "message": "Qdrant vector store is not available"},
        )

    # Get Ollama provider
    ollama_provider = providers.get("ollama")
    if ollama_provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "provider_unavailable", "message": "Ollama provider is not available"},
        )

    # Validate MIME type early (before service processing)
    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "unsupported_mime",
                "message": f"MIME type '{mime}' not supported. Allowed: {sorted(ALLOWED_MIMES)}",
            },
        )

    service = DocumentService(db)

    try:
        from rain_backend.settings import settings
        result = await service.upload_document(
            file=file,
            minio_client=minio_client,
            qdrant_client=qdrant_client,
            ollama_provider=ollama_provider,
            settings=settings,
        )
        return result
    except ValueError as e:
        # Unsupported file type, too large, or decode failure
        if "Unsupported MIME" in str(e):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={"code": "unsupported_mime", "message": str(e)},
            )
        if "too large" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"code": "file_too_large", "message": str(e)},
            )
        if "decode" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "decode_error", "message": str(e)},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_request", "message": str(e)},
        )
    except RuntimeError as e:
        # Embedding failure
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "embedding_error", "message": str(e)},
        )
    except Exception as e:
        logger.exception(f"Unexpected error during document upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal", "message": f"Document processing failed: {str(e)}"},
        )


@router.get("/{document_id}/view")
async def view_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio_client=Depends(get_minio),
) -> Response:
    """Serve a file inline (for image display in chat history)."""
    from rain_backend.settings import settings
    service = DocumentService(db)
    filename, content = await service.get_document_content(document_id, minio_client, settings)
    if content is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Document not found"})

    # Determine mime from DB
    from sqlalchemy import select as _select
    from db.schemas import Document as _Doc
    _res = await db.execute(_select(_Doc).where(_Doc.id == document_id))
    _doc = _res.scalar_one_or_none()
    mime = _doc.mime if _doc else "application/octet-stream"
    return Response(content=content, media_type=mime)


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio_client=Depends(get_minio),
) -> Response:
    """Download the original file for a document."""
    from rain_backend.settings import settings
    service = DocumentService(db)
    filename, content = await service.get_document_content(document_id, minio_client, settings)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Document not found or storage unavailable"},
        )
    safe_name = filename.replace('"', '\\"')
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio_client=Depends(get_minio),
    qdrant_client=Depends(get_qdrant),
) -> None:
    """Delete a document and its associated data from all stores."""
    service = DocumentService(db)
    from rain_backend.settings import settings

    success = await service.delete_document(
        document_id=document_id,
        minio_client=minio_client,
        qdrant_client=qdrant_client,
        settings=settings,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Document not found"},
        )
