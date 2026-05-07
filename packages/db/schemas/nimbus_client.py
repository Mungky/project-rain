from datetime import datetime
from typing import List
from sqlalchemy import Boolean, String, ARRAY, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class NimbusClient(Base):
    __tablename__ = "nimbus_clients"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, server_default=text("'{}'"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=datetime.utcnow)
