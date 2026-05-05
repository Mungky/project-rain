from enum import Enum
from uuid import UUID
from sqlalchemy import ForeignKey, String, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDPKMixin, TimestampMixin


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class AgentTask(Base, UUIDPKMixin, TimestampMixin):
    """A specific step within an AgentRun."""
    __tablename__ = "agent_tasks"

    run_id: Mapped[UUID] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    
    # Order in the sequence
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Execution
    agent_role: Mapped[str] = mapped_column(String(50), comment="planner, worker, or critic")
    model_id: Mapped[str | None] = mapped_column(String(100))
    
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus), default=TaskStatus.pending, nullable=False
    )
    
    input_data: Mapped[dict | None] = mapped_column(JSONB)
    output_data: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    
    # Relationships
    run: Mapped["AgentRun"] = relationship(back_populates="tasks")

    __table_args__ = (
        {"comment": "Individual steps or tool-calls within an autonomous run."}
    )
