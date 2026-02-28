import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import String, Text, Enum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class JobStatus(str, enum.Enum):
    pending = "pending"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    gpu_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("gpus.id"), nullable=True  # assigned after matching
    )
    script_path: Mapped[str] = mapped_column(String, nullable=False)
    requirements_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.pending, nullable=False
    )
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationships
    client = relationship("User", back_populates="jobs")
    gpu = relationship("GPU", back_populates="jobs")
