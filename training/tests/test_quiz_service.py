import pytest
from unittest.mock import MagicMock, patch
from training import models, schemas
from training.errors import IncompleteQuizResponseError
from training.services import QuizService, Certificate
from training.repositories import QuizRepository, QuizCompletionRepository, CertificateRepository
from sqlalchemy.orm import Session
from .factories import QuizCompletionFactory


@patch.object(QuizRepository, "find_by_id")
@patch.object(QuizCompletionRepository, "create")
@patch.object(CertificateRepository, "get_certificate_by_id")
@patch.object(Certificate, "generate_pdf")
@patch.object(QuizService, "email_certificate")
def test_grade_passing(
        mock_quiz_service_email_certificate: MagicMock,
        mock_certificate_service_generate_pdf: MagicMock,
        mock_certificate_repo_get_certificate_by_id: MagicMock,
        mock_quiz_completion_repo_create: MagicMock,
        mock_quiz_repo_find_by_id: MagicMock,
        db_with_data: Session,
        valid_passing_submission: schemas.QuizSubmission,
        valid_quiz: models.Quiz,
        valid_user_certificate: schemas.UserCertificate
):
    quiz_service = QuizService(db_with_data)
    mock_quiz_repo_find_by_id.return_value = valid_quiz
    mock_quiz_completion_repo_create.return_value = QuizCompletionFactory.build()
    mock_certificate_repo_get_certificate_by_id.return_value = valid_user_certificate
    mock_certificate_service_generate_pdf.return_value = bytearray()
    mock_quiz_service_email_certificate.return_value = None

    result = quiz_service.grade(quiz_id=123, user_id=123, submission=valid_passing_submission)

    assert isinstance(result, schemas.QuizGrade)
    assert result.passed
    assert result.percentage == 1
    assert result.questions[0].correct_ids == [0]
    assert result.questions[0].selected_ids == [0]
    assert result.questions[1].correct_ids == [1]
    assert result.questions[1].selected_ids == [1]


@patch.object(QuizRepository, "find_by_id")
@patch.object(QuizCompletionRepository, "create")
def test_grade_failing(
        mock_quiz_completion_repo_create: MagicMock,
        mock_quiz_repo_find_by_id: MagicMock,
        db_with_data: Session,
        valid_failing_submission: schemas.QuizSubmission,
        valid_quiz: models.Quiz
):
    quiz_service = QuizService(db_with_data)
    mock_quiz_repo_find_by_id.return_value = valid_quiz
    mock_quiz_completion_repo_create.return_value = QuizCompletionFactory.build()

    result = quiz_service.grade(quiz_id=123, user_id=123, submission=valid_failing_submission)

    assert isinstance(result, schemas.QuizGrade)
    assert not result.passed
    assert result.percentage == 0.5
    assert result.questions[0].correct_ids == []
    assert result.questions[0].selected_ids == [1]
    assert result.questions[1].correct_ids == []
    assert result.questions[1].selected_ids == [1]


@patch.object(QuizRepository, "find_by_id")
@patch.object(QuizCompletionRepository, "create")
def test_grade_invalid(
        mock_quiz_completion_repo_create: MagicMock,
        mock_quiz_repo_find_by_id: MagicMock,
        db_with_data: Session,
        invalid_submission: schemas.QuizSubmission,
        valid_quiz: models.Quiz
):
    quiz_service = QuizService(db_with_data)
    mock_quiz_repo_find_by_id.return_value = valid_quiz
    mock_quiz_completion_repo_create.return_value = 0

    with pytest.raises(IncompleteQuizResponseError) as err:
        quiz_service.grade(quiz_id=123, user_id=123, submission=invalid_submission)

    assert err.value.missing_responses == [1]
