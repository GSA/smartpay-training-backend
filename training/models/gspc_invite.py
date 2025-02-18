from datetime import datetime, date
import uuid
from training.models import Base
from sqlalchemy import UUID, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column


class GspcInvite(Base):
    __tablename__ = "gspc_invite"

    id: Mapped[int] = mapped_column(primary_key=True)
    gspc_invite_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(unique=False)
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    certification_expiration_date: Mapped[date] = mapped_column(Date(), nullable=False)
    second_invite_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_invite_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "gspc_invite_id": str(self.gspc_invite_id) if self.gspc_invite_id else None,
            "email": self.email,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "certification_expiration_date": self.certification_expiration_date.isoformat() if self.certification_expiration_date else None,
            "second_invite_date": self.second_invite_date.isoformat() if self.second_invite_date else None,
            "final_invite_date": self.final_invite_date.isoformat() if self.final_invite_date else None,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None
        }
