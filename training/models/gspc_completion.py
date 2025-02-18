from typing import Any
from datetime import date, datetime
from training.models import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, func


class GspcCompletion(Base):
    __tablename__ = "gspc_completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    passed: Mapped[bool] = mapped_column()
    certification_expiration_date: Mapped[date] = mapped_column(nullable=False)
    submit_ts: Mapped[datetime] = mapped_column(server_default=func.now())
    responses: Mapped[dict[str, Any]] = mapped_column()
