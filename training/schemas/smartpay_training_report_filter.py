from pydantic import ConfigDict, BaseModel
from datetime import datetime
from typing import List, Optional


class SmartPayTrainingReportFilter(BaseModel):
    agency_id: Optional[int] = None
    bureau_id: Optional[int] = None
    completion_date_start: Optional[datetime] = None
    completion_date_end: Optional[datetime] = None
    quiz_names: Optional[List[str]] = None
    model_config = ConfigDict(from_attributes=True)
