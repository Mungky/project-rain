from datetime import datetime
from sqlalchemy import Boolean, String, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class NimbusProject(Base):
    __tablename__ = "nimbus_projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    client_code: Mapped[str] = mapped_column(String(30), ForeignKey("nimbus_clients.code", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    default_folder_category: Mapped[str] = mapped_column(String(20), nullable=False, default="MISC")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=datetime.utcnow)
