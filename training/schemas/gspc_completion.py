
from datetime import date
from typing import Any
import uuid
from pydantic import BaseModel


class GspcCompletion(BaseModel):
    user_id: int
    passed: bool
    gspc_invite_id: uuid.UUID
    certification_expiration_date: date
    responses: dict[str, Any]
