from datetime import datetime, date
from pydantic import ConfigDict, BaseModel


class GspcCertificate(BaseModel):
    user_id: int
    user_name: str
    agency: str
    certification_expiration_date: date
    completion_date: datetime
    model_config = ConfigDict(from_attributes=True)
