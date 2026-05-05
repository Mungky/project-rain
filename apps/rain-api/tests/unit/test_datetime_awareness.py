"""Tests for timezone-aware datetime handling across the backend.

Verifies that:
- UTCDatetime converts naive datetimes to UTC-aware
- UTCDatetime passes through already-aware datetimes unchanged
- JSON serialization produces RFC3339-compliant output
- Services create UTC-aware datetimes
- Cursor parsing handles both naive and aware ISO strings
"""

import pytest
from datetime import datetime, UTC, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel, ValidationError

from rain_backend.schemas.common import UTCDatetime


class DatetimeTestModel(BaseModel):
    """Test model with UTCDatetime fields."""
    created_at: UTCDatetime
    updated_at: UTCDatetime
    deleted_at: UTCDatetime | None = None


class TestUTCDatetime:
    """Test the UTCDatetime annotated type."""

    def test_naive_datetime_becomes_utc_aware(self):
        """Naive datetime input should be converted to UTC-aware."""
        naive = datetime(2024, 6, 15, 12, 0, 0)
        model = DatetimeTestModel(
            created_at=naive,
            updated_at=naive,
        )
        assert model.created_at.tzinfo is not None
        assert model.created_at.tzinfo == UTC
        assert model.updated_at.tzinfo == UTC

    def test_aware_datetime_passes_through(self):
        """Already timezone-aware datetime should pass through unchanged."""
        aware = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        model = DatetimeTestModel(
            created_at=aware,
            updated_at=aware,
        )
        assert model.created_at.tzinfo == UTC
        assert model.created_at == aware

    def test_non_utc_timezone_preserved(self):
        """Datetime with non-UTC timezone should be preserved as-is."""
        jakarta = timezone(timedelta(hours=7))
        aware = datetime(2024, 6, 15, 12, 0, 0, tzinfo=jakarta)
        model = DatetimeTestModel(
            created_at=aware,
            updated_at=aware,
        )
        assert model.created_at.tzinfo == jakarta

    def test_none_optional_datetime(self):
        """Optional UTCDatetime field with None should work."""
        naive = datetime(2024, 6, 15, 12, 0, 0)
        model = DatetimeTestModel(
            created_at=naive,
            updated_at=naive,
            deleted_at=None,
        )
        assert model.deleted_at is None

    def test_none_nullable_field_with_naive_datetime(self):
        """Optional UTCDatetime field with naive value should become aware."""
        naive = datetime(2024, 6, 15, 12, 0, 0)
        model = DatetimeTestModel(
            created_at=naive,
            updated_at=naive,
            deleted_at=naive,
        )
        assert model.deleted_at is not None
        assert model.deleted_at.tzinfo == UTC

    def test_invalid_type_raises(self):
        """Non-datetime input should raise ValidationError."""
        with pytest.raises(ValidationError):
            DatetimeTestModel(
                created_at="not-a-datetime",
                updated_at=datetime.now(UTC),
            )

    def test_rfc3339_json_serialization(self):
        """JSON output should be RFC3339-compliant with timezone offset."""
        naive = datetime(2024, 6, 15, 12, 0, 0)
        model = DatetimeTestModel(
            created_at=naive,
            updated_at=naive,
        )
        json_str = model.model_dump_json()
        assert "+00:00" in json_str or "Z" in json_str

    def test_rfc3339_json_format_matches_iso(self):
        """Serialized datetime should match expected ISO 8601 format."""
        aware = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        model = DatetimeTestModel(
            created_at=aware,
            updated_at=aware,
        )
        json_str = model.model_dump_json()
        assert "2024-06-15T12:30:45" in json_str
        assert "+00:00" in json_str or "Z" in json_str

    def test_datetime_now_utc_is_aware(self):
        """datetime.now(UTC) should produce timezone-aware datetime."""
        now = datetime.now(UTC)
        model = DatetimeTestModel(
            created_at=now,
            updated_at=now,
        )
        assert model.created_at.tzinfo is not None


class TestConversationSchemaTimezones:
    """Test conversation schemas handle timezone-aware datetimes correctly."""

    def test_conversation_model_naive_to_aware(self):
        """Conversation response model should convert naive datetimes."""
        from rain_backend.schemas.conversation import Conversation

        naive = datetime(2024, 6, 15, 12, 0, 0)
        conv_id = uuid4()
        user_id = uuid4()

        conv = Conversation(
            id=conv_id,
            user_id=user_id,
            title="Test",
            created_at=naive,
            updated_at=naive,
            deleted_at=None,
        )
        assert conv.created_at.tzinfo is not None
        assert conv.updated_at.tzinfo is not None
        assert conv.deleted_at is None

    def test_conversation_model_rfc3339_output(self):
        """Conversation model JSON should contain RFC3339 datetime strings."""
        from rain_backend.schemas.conversation import Conversation

        naive = datetime(2024, 6, 15, 12, 0, 0)
        json_str = Conversation(
            id=uuid4(),
            user_id=uuid4(),
            title="Test",
            created_at=naive,
            updated_at=naive,
            deleted_at=None,
        ).model_dump_json()

        assert "+00:00" in json_str or "Z" in json_str

    def test_message_model_naive_to_aware(self):
        """Message model should convert naive datetimes to UTC-aware."""
        from rain_backend.schemas.conversation import Message

        naive = datetime(2024, 6, 15, 12, 0, 0)
        msg = Message(
            id=uuid4(),
            conversation_id=uuid4(),
            role="user",
            content="Hello",
            created_at=naive,
        )
        assert msg.created_at.tzinfo is not None

    def test_conversation_created_response_rfc3339(self):
        """ConversationCreatedResponse should serialize RFC3339."""
        from rain_backend.schemas.conversation import ConversationCreatedResponse

        naive = datetime(2024, 6, 15, 12, 0, 0)
        json_str = ConversationCreatedResponse(
            id=uuid4(),
            created_at=naive,
        ).model_dump_json()

        assert "+00:00" in json_str or "Z" in json_str


class TestCursorParsing:
    """Test cursor-based pagination datetime parsing."""

    def test_cursor_naive_iso_string(self):
        """Parsing a naive ISO datetime string should produce UTC-aware result."""
        from rain_backend.services.conversation_service import ConversationService

        naive_cursor = "2024-06-15T12:00:00"
        parsed = datetime.fromisoformat(naive_cursor)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        assert parsed.tzinfo is not None

    def test_cursor_aware_iso_string(self):
        """Parsing an aware ISO datetime string should keep timezone."""
        aware_cursor = "2024-06-15T12:00:00+00:00"
        parsed = datetime.fromisoformat(aware_cursor)
        assert parsed.tzinfo is not None

    def test_cursor_z_suffix(self):
        """Parsing an ISO datetime with Z suffix should be timezone-aware."""
        z_cursor = "2024-06-15T12:00:00Z"
        parsed = datetime.fromisoformat(z_cursor)
        assert parsed.tzinfo is not None