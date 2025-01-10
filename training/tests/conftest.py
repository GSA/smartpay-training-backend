from collections.abc import Generator
from unittest.mock import MagicMock, patch
import jwt
from pydantic import TypeAdapter
import pytest
import yaml
import pathlib
from datetime import datetime
from training.api.deps import agency_repository, quiz_repository, quiz_service, user_repository
from training.database import engine
from training import models, schemas
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import event
from training.repositories import (AgencyRepository, UserRepository, QuizRepository, QuizCompletionRepository,
                                   CertificateRepository, RoleRepository, GspcCompletionRepository)
from training.schemas import AgencyCreate, RoleCreate, UserCertificate, GspcCertificate
from training.services import QuizService
from training.config import settings
from . import factories
from training.main import app

quiz_submission_adapter = TypeAdapter(schemas.QuizSubmission)
gspc_submission_adapter = TypeAdapter(schemas.GspcSubmission)


@pytest.fixture
def db():
    '''
    This fixture initiates a transactional DB session and rolls back all
    changes after the test case completes.
    '''

    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False)
    session = SessionLocal(bind=connection)
    session.begin_nested()
    already_rolled_back = False

    @event.listens_for(session, "after_rollback")
    def mark_rolled_back(_):
        '''
        The DB session is designed to rollback upon an exception, so no need to
        repeat a rollback if one has already been performed.
        '''
        nonlocal already_rolled_back
        already_rolled_back = True

    yield session

    session.close()
    if not already_rolled_back:
        transaction.rollback()
    connection.close()


@pytest.fixture
def db_with_data(db: Session, testdata: dict):
    '''
    Provides a fully populated database.
    '''

    agency_ids = []
    user_ids = []
    quiz_ids = []

    for data in testdata["agencies"]:
        agency = models.Agency(name=data["name"], bureau=data["bureau"])
        db.add(agency)
        db.commit()
        db.refresh(agency)
        agency_ids.append(agency.id)

    for index, user in enumerate(testdata["users"]):
        user = models.User(email=user["email"], name=user["name"], agency_id=agency_ids[index % 2], created_by=user["created_by"])
        db.add(user)
        db.commit()
        db.refresh(user)
        user_ids.append(user.id)

    for index, quiz in enumerate(testdata["quizzes"]):
        quiz = models.Quiz(
            name=quiz["name"],
            topic=quiz["topic"],
            audience=quiz["audience"],
            active=quiz["active"],
            content=quiz["content"]
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        quiz_ids.append(quiz.id)

    quiz_completion_pass = models.QuizCompletion(user_id=user_ids[-1], quiz_id=quiz_ids[-1], passed=True,
                                                 submit_ts=datetime(2024, 1, 24))
    db.add(quiz_completion_pass)
    db.commit()

    quiz_completion_fail = models.QuizCompletion(user_id=user_ids[-1], quiz_id=quiz_ids[-1], passed=False,
                                                 submit_ts=datetime(2024, 1, 24))
    db.add(quiz_completion_fail)
    db.commit()
    for role in testdata["roles"]:
        role = models.Role(name=role["name"])
        db.add(role)
        db.commit()
    yield db


@pytest.fixture
def testdata() -> dict:
    '''
    Provides a dictionary of test values from testdata.yaml. These values are
    loaded into the test database in the db_with_data fixture.
    '''
    datafile_path = pathlib.PurePath(pathlib.Path(__file__).parent.resolve(), "testdata.yaml")
    with open(datafile_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def valid_user_ids(db_with_data: Session) -> Generator[list[int], None, None]:
    '''
    Provides a list of user IDs that have been loaded into the test database.
    '''
    users = db_with_data.query(models.User).all()
    user_ids = list(map(lambda user: user.id, users))
    yield user_ids


@pytest.fixture
def valid_quiz_ids(db_with_data: Session) -> Generator[list[int], None, None]:
    '''
    Provides a list of quiz IDs that have been loaded into the test database.
    '''
    quizzes = db_with_data.query(models.Quiz).all()
    quiz_ids = list(map(lambda quiz: quiz.id, quizzes))
    yield quiz_ids


@pytest.fixture
def valid_agency(testdata: dict) -> Generator[AgencyCreate, None, None]:
    '''
    Provides a valid agency.
    '''
    jsondata = testdata["agencies"][0]
    agency = AgencyCreate(name=jsondata["name"], bureau=jsondata["bureau"])
    yield agency


@pytest.fixture
def valid_user_dict(testdata: dict) -> Generator[dict, None, None]:
    '''
    Provides a dict containing valid values for a user.
    '''
    yield testdata["users"][0]


@pytest.fixture
def valid_jwt(db_with_data: Session) -> str:
    '''
    Provides a JWT based on a test user in the database.
    '''
    db_user = db_with_data.query(models.User).first()
    user = schemas.UserJWT.model_validate(db_user).model_dump()
    return jwt.encode(user, settings.JWT_SECRET, algorithm="HS256")


@pytest.fixture
def agency_repo_empty(db: Session) -> Generator[AgencyRepository, None, None]:
    '''
    Provides an AgencyRepository injected with an empty database.
    '''
    yield AgencyRepository(session=db)


@pytest.fixture
def agency_repo_with_data(db_with_data: Session) -> Generator[AgencyRepository, None, None]:
    '''
    Provides an AgencyRepository injected with a populated database.
    '''
    yield AgencyRepository(session=db_with_data)


@pytest.fixture
def user_repo_empty(db: Session) -> Generator[UserRepository, None, None]:
    '''
    Provides an UserRepository injected with an empty database.
    '''
    yield UserRepository(session=db)


@pytest.fixture
def user_repo_with_data(db_with_data: Session) -> Generator[UserRepository, None, None]:
    '''
    Provides an UserRepository injected with a populated database.
    '''
    yield UserRepository(session=db_with_data)


@pytest.fixture
def quiz_repo_empty(db: Session) -> Generator[QuizRepository, None, None]:
    '''
    Provides a QuizRepository injected with an empty database.
    '''
    yield QuizRepository(session=db)


@pytest.fixture
def quiz_completion_repo_with_data(db_with_data: Session) -> Generator[QuizCompletionRepository, None, None]:
    '''
    Provides a QuizCompletionRepository injected with a populated database.
    '''
    yield QuizCompletionRepository(session=db_with_data)


@pytest.fixture
def quiz_repo_with_data(db_with_data: Session) -> Generator[QuizRepository, None, None]:
    '''
    Provides a QuizRepository injected with a populated database.
    '''
    yield QuizRepository(session=db_with_data)


@pytest.fixture
def valid_passing_submission(testdata: dict) -> Generator[schemas.QuizSubmission, None, None]:
    '''
    Provides a QuizSubmission schema object containing valid passing responses.
    '''
    jsondata = testdata["quiz_submissions"]["valid_passing"]
    yield quiz_submission_adapter.validate_python(jsondata)


@pytest.fixture
def valid_failing_submission(testdata: dict) -> Generator[schemas.QuizSubmission, None, None]:
    '''
    Provides a QuizSubmission schema object containing valid failing responses.
    '''
    jsondata = testdata["quiz_submissions"]["valid_failing"]
    yield quiz_submission_adapter.validate_python(jsondata)


@pytest.fixture
def invalid_submission(testdata: dict) -> Generator[schemas.QuizSubmission, None, None]:
    '''
    Provides a QuizSubmission schema object containing an incomplete set of
    responses.
    '''
    jsondata = testdata["quiz_submissions"]["invalid_incomplete"]
    yield quiz_submission_adapter.validate_python(jsondata)


@pytest.fixture
def valid_quiz(testdata: dict) -> Generator[models.Quiz, None, None]:
    '''
    Provides a valid Quiz database model object.
    '''
    jsondata = testdata["quizzes"][0]
    db_quiz = models.Quiz(**jsondata)
    db_quiz.id = 123
    yield db_quiz


@pytest.fixture
def valid_quiz_create() -> schemas.QuizCreate:
    '''
    Provides a valid QuizCreate schema object.
    '''
    return factories.QuizCreateSchemaFactory.build(active=True)


@pytest.fixture
def cert_repo_with_data(db_with_data: Session) -> Generator[CertificateRepository, None, None]:
    '''
    Provides an CertificateRepository injected with a populated database.
    '''
    yield CertificateRepository(session=db_with_data)


@pytest.fixture
def passed_quiz_completion_id(db_with_data: Session) -> Generator[int, None, None]:
    '''
    Provides quiz completion id that have passed value equals true
    '''
    quiz_comletion_passed = db_with_data.query(models.QuizCompletion).filter(models.QuizCompletion.passed).first().id
    yield quiz_comletion_passed


@pytest.fixture
def mock_quiz_repo() -> Generator[QuizRepository, None, None]:
    mock = MagicMock()
    app.dependency_overrides[quiz_repository] = lambda: mock
    yield mock
    app.dependency_overrides = {}


@pytest.fixture
def mock_quiz_service() -> Generator[QuizService, None, None]:
    mock = MagicMock()
    app.dependency_overrides[quiz_service] = lambda: mock
    yield mock
    app.dependency_overrides = {}


@pytest.fixture
def mock_user_repo() -> Generator[UserRepository, None, None]:
    mock = MagicMock()
    app.dependency_overrides[user_repository] = lambda: mock
    yield mock
    app.dependency_overrides = {}


@pytest.fixture
def mock_agency_repo() -> Generator[AgencyRepository, None, None]:
    mock = MagicMock()
    app.dependency_overrides[agency_repository] = lambda: mock
    yield mock
    app.dependency_overrides = {}


@pytest.fixture
def role_repo_empty(db: Session) -> Generator[RoleRepository, None, None]:
    '''
    Provides an RoleRepository injected with an empty database.
    '''
    yield RoleRepository(session=db)


@pytest.fixture
def role_repo_with_data(db_with_data: Session) -> Generator[RoleRepository, None, None]:
    '''
    Provides an RoleRepository injected with a populated database.
    '''
    yield RoleRepository(session=db_with_data)


@pytest.fixture
def valid_role(testdata: dict) -> Generator[RoleCreate, None, None]:
    '''
    Provides a valid agency.
    '''
    jsondata = testdata["roles"][0]
    role = RoleCreate(name=jsondata["name"])
    yield role


@pytest.fixture
def valid_user_certificate() -> Generator[schemas.UserCertificate, None, None]:
    testdata = {
        'id': 1,
        'user_id': 2,
        'user_name': "Molly",
        'agency': 'Freeman Journal',
        'quiz_id': 123,
        'quiz_name': "Travel Training for Agency/Organization Program Coordinators",
        'completion_date': '2023-08-21T22:59:36'
    }
    yield UserCertificate.model_validate(testdata)


@pytest.fixture
def gspc_completion_repo_with_data(db_with_data: Session) -> Generator[GspcCompletionRepository, None, None]:
    '''
    Provides a GspcCompletionRepository injected with a populated database.
    '''
    yield GspcCompletionRepository(session=db_with_data)


@pytest.fixture
def valid_gspc_certificate() -> Generator[schemas.GspcCertificate, None, None]:
    '''
    Provides a GspcCertificate schema object.
    '''
    testdata = {
        'user_id': 2,
        'user_name': "Molly",
        'agency': 'Freeman Journal',
        'certification_expiration_date': '2099-01-01',
        'completion_date': '2023-08-21T22:59:36'
    }
    yield GspcCertificate.model_validate(testdata)


@pytest.fixture
def valid_gspc_passing_submission(testdata: dict) -> Generator[schemas.GspcSubmission, None, None]:
    '''
    Provides a GspcSubmission schema object containing valid passing responses.
    '''
    jsondata = testdata["gspc_submission"]["valid_passing"]
    yield gspc_submission_adapter.validate_python(jsondata)


@pytest.fixture
def valid_gspc_failing_submission(testdata: dict) -> Generator[schemas.GspcSubmission, None, None]:
    '''
    Provides a GspcSubmission schema object containing invalid passing responses.
    '''
    jsondata = testdata["gspc_submission"]["valid_failing"]
    yield gspc_submission_adapter.validate_python(jsondata)


@pytest.fixture
def smtp_instance():
    with patch('training.services.quiz.SMTP') as smtp_mock:
        with smtp_mock() as smtp:
            yield smtp


@pytest.fixture
def gspc_smtp_instance():
    with patch('training.services.gspc.SMTP') as smtp_mock:
        with smtp_mock() as smtp:
            yield smtp
