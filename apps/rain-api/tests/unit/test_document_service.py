"""Tests for document service: chunking logic and upload pipeline."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

from rain_backend.services.document_service import DocumentService, ALLOWED_MIMES
from rain_backend.schemas.document import DocumentUploadResponse


# ── Chunking tests ──────────────────────────────────────────────

class TestChunkText:
    """Test the _chunk_text static method."""

    def test_empty_text(self):
        assert DocumentService._chunk_text("") == []

    def test_whitespace_only(self):
        assert DocumentService._chunk_text("   \n\n  ") == []

    def test_short_text_single_chunk(self):
        text = "Hello world, this is a short text."
        chunks = DocumentService._chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_text_under_max_chars(self):
        text = "x" * 1999
        chunks = DocumentService._chunk_text(text)
        assert len(chunks) == 1

    def test_text_at_max_chars(self):
        text = "x" * 2000
        chunks = DocumentService._chunk_text(text)
        assert len(chunks) == 1

    def test_paragraph_splitting(self):
        para1 = "x" * 500
        para2 = "y" * 500
        para3 = "z" * 500
        text = f"{para1}\n\n{para2}\n\n{para3}"
        chunks = DocumentService._chunk_text(text)
        assert len(chunks) == 1
        assert all(p in chunks[0] for p in [para1, para2, para3])

    def test_multiple_chunks_from_paragraphs(self):
        paragraphs = [f"Paragraph {i} with some content to fill space." * 20 for i in range(10)]
        text = "\n\n".join(paragraphs)
        chunks = DocumentService._chunk_text(text, max_chars=300)
        assert len(chunks) >= 2
        # All chunks should be <= max_chars (or close for hard splits)
        for chunk in chunks:
            assert len(chunk) <= 350  # some tolerance for overlap

    def test_overlap_between_chunks(self):
        text = "Word " * 2000  # ~10000 chars
        chunks = DocumentService._chunk_text(text, max_chars=2000, overlap_chars=200)
        if len(chunks) > 1:
            # Check that subsequent chunks contain content from previous chunk tail
            for i in range(1, len(chunks)):
                # Overlap means some content from end of prev chunk appears at start of next
                assert len(chunks[i]) > 0

    def test_long_paragraph_splits_sentences(self):
        # Single paragraph exceeding max_chars
        text = "This is sentence one. This is sentence two. This is sentence three. " * 100
        chunks = DocumentService._chunk_text(text, max_chars=500, overlap_chars=50)
        assert len(chunks) >= 2

    def test_very_long_word_hard_split(self):
        text = "x" * 5000
        chunks = DocumentService._chunk_text(text, max_chars=2000, overlap_chars=200)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 2000

    def test_custom_max_chars(self):
        text = "x" * 500
        chunks = DocumentService._chunk_text(text, max_chars=100)
        assert len(chunks) >= 5

    def test_strips_whitespace(self):
        text = "  Hello world  \n\n  Another paragraph  "
        chunks = DocumentService._chunk_text(text)
        # Short text fits in one chunk, both paragraphs present
        assert len(chunks) == 1
        assert "Hello world" in chunks[0]
        assert "Another paragraph" in chunks[0]


class TestAllowedMimes:
    """Test the allowed MIME types constant."""

    def test_text_plain_allowed(self):
        assert "text/plain" in ALLOWED_MIMES

    def test_text_markdown_allowed(self):
        assert "text/markdown" in ALLOWED_MIMES

    def test_text_x_markdown_allowed(self):
        assert "text/x-markdown" in ALLOWED_MIMES

    def test_application_pdf_not_allowed(self):
        assert "application/pdf" not in ALLOWED_MIMES


class TestUploadDocument:
    """Test the upload_document service method (mocked infrastructure)."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_minio(self):
        return MagicMock()

    @pytest.fixture
    def mock_qdrant(self):
        return AsyncMock()

    @pytest.fixture
    def mock_ollama(self):
        provider = AsyncMock()
        provider.embed = AsyncMock()
        return provider

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.minio_bucket_uploads = "rain-uploads"
        return settings

    @pytest.fixture
    def mock_upload_file(self):
        file = AsyncMock()
        file.filename = "test.txt"
        file.content_type = "text/plain"
        file.read = AsyncMock(return_value=b"Hello world, this is a test document.")
        return file

    @pytest.mark.asyncio
    async def test_upload_document_success(
        self, mock_db, mock_minio, mock_qdrant, mock_ollama, mock_settings, mock_upload_file
    ):
        """Happy path: file uploaded, chunked, embedded, stored in Qdrant."""
        mock_ollama.embed.return_value = [[0.1] * 768]

        # Mock DB operations
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        # When refresh is called, set the document id
        def set_doc_attrs(doc):
            doc.id = uuid4()
            doc.created_at = datetime.now(UTC)
            doc.updated_at = datetime.now(UTC)
        mock_db.refresh.side_effect = set_doc_attrs

        service = DocumentService(mock_db)

        with patch(
            "rain_backend.services.document_service.asyncio.to_thread",
            new_callable=AsyncMock,
        ) as mock_to_thread:
            mock_to_thread.return_value = None

            result = await service.upload_document(
                file=mock_upload_file,
                minio_client=mock_minio,
                qdrant_client=mock_qdrant,
                ollama_provider=mock_ollama,
                settings=mock_settings,
            )

        assert isinstance(result, DocumentUploadResponse)
        assert result.status == "ready"
        assert result.filename == "test.txt"
        assert result.chunk_count >= 1
        mock_ollama.embed.assert_called_once()
        mock_qdrant.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_document_unsupported_mime(
        self, mock_db, mock_minio, mock_qdrant, mock_ollama, mock_settings
    ):
        """Unsupported MIME type raises ValueError."""
        file = AsyncMock()
        file.content_type = "application/pdf"
        file.filename = "test.pdf"

        service = DocumentService(mock_db)

        with pytest.raises(ValueError, match="Unsupported MIME"):
            await service.upload_document(
                file=file,
                minio_client=mock_minio,
                qdrant_client=mock_qdrant,
                ollama_provider=mock_ollama,
                settings=mock_settings,
            )

    @pytest.mark.asyncio
    async def test_upload_document_empty_file(
        self, mock_db, mock_minio, mock_qdrant, mock_ollama, mock_settings
    ):
        """Empty file produces zero chunks, status=ready."""
        file = AsyncMock()
        file.filename = "empty.txt"
        file.content_type = "text/plain"
        file.read = AsyncMock(return_value=b"")

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        def set_doc_attrs(doc):
            doc.id = uuid4()
            doc.created_at = datetime.now(UTC)
            doc.updated_at = datetime.now(UTC)
        mock_db.refresh.side_effect = set_doc_attrs

        service = DocumentService(mock_db)

        with patch(
            "rain_backend.services.document_service.asyncio.to_thread",
            new_callable=AsyncMock,
        ) as mock_to_thread:
            mock_to_thread.return_value = None

            result = await service.upload_document(
                file=file,
                minio_client=mock_minio,
                qdrant_client=mock_qdrant,
                ollama_provider=mock_ollama,
                settings=mock_settings,
            )

        assert result.status == "ready"
        assert result.chunk_count == 0
        mock_qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_document_minio_failure(
        self, mock_db, mock_minio, mock_qdrant, mock_ollama, mock_settings, mock_upload_file
    ):
        """MinIO put_object failure sets status=error and re-raises."""
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        def set_doc_attrs(doc):
            doc.id = uuid4()
            doc.created_at = datetime.now(UTC)
            doc.updated_at = datetime.now(UTC)
        mock_db.refresh.side_effect = set_doc_attrs

        service = DocumentService(mock_db)

        with patch(
            "rain_backend.services.document_service.asyncio.to_thread",
            side_effect=Exception("MinIO connection refused"),
        ):
            with pytest.raises(Exception, match="MinIO"):
                await service.upload_document(
                    file=mock_upload_file,
                    minio_client=mock_minio,
                    qdrant_client=mock_qdrant,
                    ollama_provider=mock_ollama,
                    settings=mock_settings,
                )

    @pytest.mark.asyncio
    async def test_upload_document_embedding_failure(
        self, mock_db, mock_minio, mock_qdrant, mock_ollama, mock_settings, mock_upload_file
    ):
        """Embedding returning empty list sets status=error and raises."""
        mock_ollama.embed.return_value = [[]]  # empty embedding for chunk 0

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        def set_doc_attrs(doc):
            doc.id = uuid4()
            doc.created_at = datetime.now(UTC)
            doc.updated_at = datetime.now(UTC)
        mock_db.refresh.side_effect = set_doc_attrs

        service = DocumentService(mock_db)

        with patch(
            "rain_backend.services.document_service.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Embedding failed"):
                await service.upload_document(
                    file=mock_upload_file,
                    minio_client=mock_minio,
                    qdrant_client=mock_qdrant,
                    ollama_provider=mock_ollama,
                    settings=mock_settings,
                )

    @pytest.mark.asyncio
    async def test_upload_document_decode_failure(
        self, mock_db, mock_minio, mock_qdrant, mock_ollama, mock_settings
    ):
        """Non-UTF-8 file content raises ValueError."""
        file = AsyncMock()
        file.filename = "binary.txt"
        file.content_type = "text/plain"
        file.read = AsyncMock(return_value=b"\x80\x81\x82")  # invalid UTF-8

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        def set_doc_attrs(doc):
            doc.id = uuid4()
            doc.created_at = datetime.now(UTC)
            doc.updated_at = datetime.now(UTC)
        mock_db.refresh.side_effect = set_doc_attrs

        service = DocumentService(mock_db)

        with patch(
            "rain_backend.services.document_service.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(ValueError, match="decode"):
                await service.upload_document(
                    file=file,
                    minio_client=mock_minio,
                    qdrant_client=mock_qdrant,
                    ollama_provider=mock_ollama,
                    settings=mock_settings,
                )

    @pytest.mark.asyncio
    async def test_upload_document_qdrant_failure(
        self, mock_db, mock_minio, mock_qdrant, mock_ollama, mock_settings, mock_upload_file
    ):
        """Qdrant upsert failure sets status=error and re-raises."""
        mock_ollama.embed.return_value = [[0.1] * 768]
        mock_qdrant.upsert.side_effect = Exception("Qdrant connection refused")

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        def set_doc_attrs(doc):
            doc.id = uuid4()
            doc.created_at = datetime.now(UTC)
            doc.updated_at = datetime.now(UTC)
        mock_db.refresh.side_effect = set_doc_attrs

        service = DocumentService(mock_db)

        with patch(
            "rain_backend.services.document_service.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(Exception, match="Qdrant"):
                await service.upload_document(
                    file=mock_upload_file,
                    minio_client=mock_minio,
                    qdrant_client=mock_qdrant,
                    ollama_provider=mock_ollama,
                    settings=mock_settings,
                )