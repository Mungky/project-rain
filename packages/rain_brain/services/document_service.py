"""Service layer for document upload, chunking, embedding, and storage."""

import asyncio
import logging
import re
from datetime import datetime, UTC
from io import BytesIO
from uuid import UUID, uuid5

from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas import Document as DocumentModel
from db.schemas.document import DocumentStatus
from db.schemas.dto_document import DocumentUploadResponse

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DOC_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
ALLOWED_MIMES = {
    "text/plain", "text/markdown", "text/x-markdown", "application/octet-stream",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # docx
    "application/msword", # doc
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", # xlsx
    "application/vnd.ms-excel", # xls
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", # pptx
    "application/ms-powerpoint", # ppt
}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


class DocumentService:
    """Service for document upload and processing."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 2000) -> list[str]:
        if not text or not text.strip(): return []
        text = text.strip()
        if len(text) <= max_chars: return [text]
        return re.split(r"\n\n+", text)

    def _extract_text(self, file_data: bytes, filename: str, mime: str) -> str:
        """Extract text from binary files based on MIME type."""
        try:
            if mime == "application/pdf" or filename.lower().endswith(".pdf"):
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(file_data))
                return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

            if mime in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword"
            ) or filename.lower().endswith((".docx", ".doc")):
                import docx
                doc = docx.Document(BytesIO(file_data))
                return "\n".join([para.text for t in doc.paragraphs if (para := t)])

            if mime in (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel"
            ) or filename.lower().endswith((".xlsx", ".xls")):
                import pandas as pd
                # Read all sheets
                df_dict = pd.read_excel(BytesIO(file_data), sheet_name=None)
                output = []
                for sheet_name, df in df_dict.items():
                    output.append(f"Sheet: {sheet_name}\n" + df.to_string(index=False))
                return "\n\n".join(output)

            # Default: try utf-8 decode for text files
            return file_data.decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Text extraction failed for {filename}: {e}")
            return f"[Error extracting text from {filename}]"

    async def upload_document(self, file: UploadFile, minio_client, qdrant_client, ollama_provider, settings) -> DocumentUploadResponse:
        filename = file.filename or "unnamed"
        mime = file.content_type or "application/octet-stream"
        
        if mime not in ALLOWED_MIMES:
            logger.warning(f"Unsupported MIME: {mime}")
            raise ValueError(f"Unsupported file type: {mime}")

        # Create row
        doc_id = uuid5(DOC_NAMESPACE, f"{filename}:{datetime.now().timestamp()}")
        minio_key = f"{DEFAULT_USER_ID}/{doc_id}/{filename}"
        
        document = DocumentModel(
            id=doc_id,
            user_id=DEFAULT_USER_ID,
            filename=filename,
            mime=mime,
            minio_key=minio_key,
            status=DocumentStatus.uploading,
        )
        self.db.add(document)
        await self.db.commit()

        try:
            # Update status to processing
            document.status = DocumentStatus.processing
            await self.db.commit()

            file_data = await file.read()
            if len(file_data) > MAX_UPLOAD_SIZE: raise ValueError("File too large")

            # 1. MinIO Storage
            logger.info(f"Storing {filename} in MinIO...")
            await asyncio.to_thread(
                minio_client.put_object,
                bucket_name=settings.minio_bucket_uploads,
                object_name=minio_key,
                data=BytesIO(file_data),
                length=len(file_data),
                content_type=mime,
            )

            # 2. Chunk & Embed
            text = self._extract_text(file_data, filename, mime)
            chunks = self._chunk_text(text)
            if chunks:
                logger.info(f"Embedding {len(chunks)} chunks using {ollama_provider.name}...")
                embeddings = await ollama_provider.embed(chunks)
                
                from qdrant_client.models import PointStruct
                points = [
                    PointStruct(
                        id=str(uuid5(DOC_NAMESPACE, f"{doc_id}:{i}")),
                        vector=embeddings[i],
                        payload={
                            "user_id": str(DEFAULT_USER_ID), 
                            "document_id": str(doc_id), 
                            "text": chunks[i], 
                            "source": filename
                        }
                    ) for i in range(len(chunks)) if i < len(embeddings) and embeddings[i]
                ]
                if points:
                    await qdrant_client.upsert(collection_name="documents", points=points)
                    logger.info(f"Successfully upserted {len(points)} vectors to Qdrant")

            # 3. Finalize
            document.status = DocumentStatus.ready
            await self.db.commit()
            
            return DocumentUploadResponse(
                id=doc_id, 
                filename=filename, 
                mime=mime, 
                status="ready", 
                chunk_count=len(chunks), 
                created_at=datetime.now(UTC)
            )

        except Exception as e:
            logger.exception(f"Upload failed: {e}")
            try:
                document.status = DocumentStatus.error
                await self.db.commit()
            except:
                pass
            raise

    async def save_chat_attachment(
        self,
        filename: str,
        mime: str,
        content_bytes: bytes,
        minio_client,
        settings,
        message_id: UUID | None = None,
    ) -> "DocumentModel":
        """Store a chat attachment in MinIO + DB. No RAG indexing (images/binary files)."""
        doc_id = uuid5(DOC_NAMESPACE, f"chat:{filename}:{datetime.now().timestamp()}")
        minio_key = f"{DEFAULT_USER_ID}/chat/{doc_id}/{filename}"

        document = DocumentModel(
            id=doc_id,
            user_id=DEFAULT_USER_ID,
            filename=filename,
            mime=mime,
            minio_key=minio_key,
            qdrant_collection="documents",
            source_type="chat",
            message_id=message_id,
            status=DocumentStatus.ready,
        )
        self.db.add(document)

        try:
            await asyncio.to_thread(
                minio_client.put_object,
                bucket_name=settings.minio_bucket_uploads,
                object_name=minio_key,
                data=BytesIO(content_bytes),
                length=len(content_bytes),
                content_type=mime,
            )
        except Exception as e:
            logger.error("Failed to store chat attachment in MinIO: %s", e)
            document.status = DocumentStatus.error

        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def list_documents(self, limit: int = 50, offset: int = 0):
        query = select(DocumentModel).where(DocumentModel.user_id == DEFAULT_USER_ID).order_by(DocumentModel.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        docs = result.scalars().all()
        count_query = select(func.count(DocumentModel.id)).where(DocumentModel.user_id == DEFAULT_USER_ID)
        count_result = await self.db.execute(count_query)
        return list(docs), count_result.scalar_one()

    async def get_document_content(self, document_id: UUID, minio_client, settings) -> tuple[str, bytes] | tuple[None, None]:
        query = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await self.db.execute(query)
        doc = result.scalar_one_or_none()
        if not doc or not minio_client:
            return None, None
        try:
            response = await asyncio.to_thread(
                minio_client.get_object,
                settings.minio_bucket_uploads,
                doc.minio_key,
            )
            content = await asyncio.to_thread(response.read)
            response.close()
            response.release_conn()
            return doc.filename, content
        except Exception as e:
            logger.error("Failed to fetch document from MinIO: %s", e)
            return None, None

    async def delete_document(self, document_id: UUID, minio_client, qdrant_client, settings) -> bool:
        query = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await self.db.execute(query)
        doc = result.scalar_one_or_none()
        if not doc: return False
        
        if qdrant_client:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                await qdrant_client.delete(collection_name="documents", points_selector=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))]))
            except: pass
        if minio_client:
            try: await asyncio.to_thread(minio_client.remove_object, settings.minio_bucket_uploads, doc.minio_key)
            except: pass
            
        await self.db.delete(doc)
        await self.db.commit()
        return True
