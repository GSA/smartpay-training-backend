import uuid
from pydantic import BaseModel, ConfigDict


class GspcSubmissionQuestion(BaseModel):
    question_id: int
    question: str
    response_id: int
    response: str
    correct: bool
    model_config = ConfigDict(from_attributes=True)


class GspcSubmissionQuestions(BaseModel):
    responses: list[GspcSubmissionQuestion]


class GspcSubmission(BaseModel):
    gspc_invite_id: uuid.UUID
    responses: GspcSubmissionQuestions
    model_config = ConfigDict(from_attributes=True)
