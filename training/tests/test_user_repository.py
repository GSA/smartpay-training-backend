from typing import List
from unittest.mock import patch
import pytest
from training import models, schemas
from training.repositories import UserRepository, AgencyRepository
from datetime import datetime, timedelta
from training.schemas import Agency, AgencyCreate
from training.tests.factories import UserSchemaFactory


def test_create(user_repo_empty: UserRepository, agency_repo_with_data: AgencyRepository):
    agency_id = agency_repo_with_data.find_all()[0].id
    new_user = schemas.UserCreate(
        email="new_user@example.com",  # type: ignore
        name="New User",
        agency_id=agency_id
    )
    db_user = user_repo_empty.create(new_user)
    assert db_user.id
    assert db_user.name == "New User"


def test_create_duplicate(user_repo_with_data: UserRepository):
    existing_user = user_repo_with_data.find_all()[0]
    duplicate_user = schemas.UserCreate(
        email=existing_user.email,  # type: ignore
        name="Duplicate User",
        agency_id=existing_user.agency_id
    )
    with pytest.raises(Exception):
        user_repo_with_data.create(duplicate_user)


def test_find_by_email(user_repo_with_data: UserRepository, valid_user_dict):
    result = user_repo_with_data.find_by_email(valid_user_dict["email"])
    assert result is not None
    assert result.name == valid_user_dict["name"]


def test_find_by_nonexistent_email(user_repo_empty: UserRepository):
    result = user_repo_empty.find_by_email("nonexistent.email@example.com")
    assert result is None


def test_save(user_repo_empty: UserRepository, agency_repo_with_data: AgencyRepository):
    agency_id = agency_repo_with_data.find_all()[0].id
    result = user_repo_empty.save(models.User(
        email="newuser@example.com",
        name="New User",
        agency_id=agency_id,
        created_by="New User"
    ))
    assert result.id
    retrieved_result = user_repo_empty.find_by_id(result.id)
    assert retrieved_result is not None
    assert retrieved_result.name == "New User"


def test_find_by_id(user_repo_with_data: UserRepository, valid_user_ids: List[int]):
    result = user_repo_with_data.find_by_id(valid_user_ids[0])
    assert result is not None
    assert result.id == valid_user_ids[0]


def test_find_by_nonexistent_id(user_repo_with_data: UserRepository, valid_user_ids):
    nonexistent_user_id = 0
    while nonexistent_user_id in valid_user_ids:
        nonexistent_user_id += 1
    result = user_repo_with_data.find_by_id(nonexistent_user_id)
    assert result is None


def test_find_all(user_repo_with_data: UserRepository, testdata: dict):
    result = user_repo_with_data.find_all()
    emails = list(map(lambda r: r.email, result))
    for valid_user in testdata["users"]:
        assert valid_user["email"] in emails


def test_delete_by_id(user_repo_with_data: UserRepository, valid_user_ids: List[int]):
    db_user = user_repo_with_data.find_by_id(valid_user_ids[0])
    db_user.roles = []
    db_user.report_agencies = []
    user_repo_with_data._session.commit()
    user_repo_with_data.delete_by_id(valid_user_ids[0])
    assert user_repo_with_data.find_by_id(valid_user_ids[0]) is None


def test_edit_user_for_reporting(user_repo_with_data: UserRepository, valid_user_ids: List[int]):
    valid_user_id = valid_user_ids[0]
    valid_agency = user_repo_with_data._session.query(models.Agency).first()
    valid_agency_list = [valid_agency.id]
    result = user_repo_with_data.edit_user_for_reporting(valid_user_id, valid_agency_list, "test_user")
    assert result is not None
    assert result.roles is not None and any(role.name == "Report" for role in result.roles)
    assert result.report_agencies is not None and any(agency.id == valid_agency.id for agency in result.report_agencies)
    assert_within_one_minute(result.modified_on)
    assert result.modified_by == "test_user"


def test_invalid_create(user_repo_with_data: UserRepository):
    invalid_user_id = 0
    invalid_agency_id_list = [0]

    with pytest.raises(Exception):
        user_repo_with_data.create(invalid_user_id, invalid_agency_id_list)


def test_get_users(user_repo_with_data: UserRepository, valid_user_ids: List[int]):
    valid_user_id = valid_user_ids[0]
    db_user = user_repo_with_data.find_by_id(valid_user_id)
    search_criteria = db_user.name[:-1]
    result = user_repo_with_data.get_users(search_criteria, 1)
    assert result is not None
    for item in result.users:
        assert search_criteria in item.name


def test_get_users_by_email(user_repo_with_data: UserRepository, valid_user_ids: List[int]):
    valid_user_id = valid_user_ids[0]
    db_user = user_repo_with_data.find_by_id(valid_user_id)
    search_criteria = db_user.email[:-1]
    result = user_repo_with_data.get_users(search_criteria, 1)
    assert result is not None
    for item in result.users:
        assert search_criteria in item.email


def assert_within_one_minute(given_datetime):
    current_datetime = datetime.now()
    difference = abs(current_datetime - given_datetime)
    assert difference < timedelta(minutes=1), f"The datetime {given_datetime} is not within one minute of the current time {current_datetime}"


def test_update_user_passing(user_repo_with_data: UserRepository, agency_repo_with_data: AgencyRepository):
    agency_id = agency_repo_with_data.find_all()[0].id
    user_id = user_repo_with_data.find_all()[0]
    updated_user = models.User(
        email="updateduser@example.com",
        name="Updated User",
        agency_id=agency_id,
    )

    result = user_repo_with_data.update_user(user_id.id, updated_user, "test_user")
    assert result is not None
    assert result.name == "Updated User"
    assert result.agency_id == agency_id
    assert result.email != "updateduser@example.com"
    assert_within_one_minute(result.modified_on)
    assert result.modified_by == "test_user"


def test_update_user_invalid_user(user_repo_with_data: UserRepository):
    invalid_user_id = 0
    updated_user = models.User(
        email="updateduser@example.com",
        name="Updated User",
        agency_id=1,
    )

    with pytest.raises(Exception):
        user_repo_with_data.update_user(invalid_user_id, updated_user, "test_user")


def test_get_admin_smartpay_training_report_no_filters(user_repo_with_data: UserRepository):
    """
    Test fetching report data without any filters applied.
    """
    report_filter = schemas.SmartPayTrainingReportFilter()
    results = user_repo_with_data.get_admin_smartpay_training_report(report_filter)
    assert len(results) > 0  # Check that we get results back
    assert all(isinstance(result, schemas.UserQuizCompletionReportData) for result in results)  # Verify type


def test_get_admin_smartpay_training_report_filter_by_date_range(user_repo_with_data: UserRepository):
    """
    Test fetching report data with completion date range filter.
    """
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 12, 31)
    report_filter = schemas.SmartPayTrainingReportFilter(completion_date_start=start_date, completion_date_end=end_date)
    results = user_repo_with_data.get_admin_smartpay_training_report(report_filter)

    assert len(results) > 0
    for result in results:
        assert start_date <= result.completion_date <= end_date


def test_get_admin_smartpay_training_report_filter_by_quiz_name(user_repo_with_data: UserRepository):
    """
    Test fetching report data by filtering with specific quiz names.
    """
    quiz_names = ["Travel Training for Ministry of Magic"]
    report_filter = schemas.SmartPayTrainingReportFilter(quiz_names=quiz_names)
    results = user_repo_with_data.get_admin_smartpay_training_report(report_filter)

    assert len(results) > 0
    assert all(result.quiz in quiz_names for result in results)


def test_get_smartpay_training_report_no_filters(user_repo_with_data: UserRepository, agency_repo_with_data: AgencyRepository):
    """
    Test fetching report data without any filters applied.
    """
    valid_agency = agency_repo_with_data.find_by_name(AgencyCreate(name="Department of Mysteries"))
    mock_user = UserSchemaFactory.build(roles=[])
    agency = Agency(id=valid_agency.id, name=valid_agency.name)
    mock_user.report_agencies.append(agency)

    # Mock the repo and RequireRole dependencies
    with patch('training.repositories.UserRepository.find_by_id', return_value=mock_user):

        report_filter = schemas.SmartPayTrainingReportFilter()
        results = user_repo_with_data.get_user_quiz_completion_report(report_filter, 1)
        assert len(results) > 0  # Check that we get results back
        assert all(isinstance(result, schemas.UserQuizCompletionReportData) for result in results)  # Verify type


def test_get_smartpay_training_report_with_filter_by_quiz_name(user_repo_with_data: UserRepository, agency_repo_with_data: AgencyRepository):
    """
    Test fetching report data with filters applied.
    """
    valid_agency = agency_repo_with_data.find_by_name(AgencyCreate(name="Department of Mysteries"))
    mock_user = UserSchemaFactory.build(roles=[])
    agency = Agency(id=valid_agency.id, name=valid_agency.name)
    mock_user.report_agencies.append(agency)

    # Mock the repo and RequireRole dependencies
    with patch('training.repositories.UserRepository.find_by_id', return_value=mock_user):

        quiz_names = ["Travel Training for Ministry of Magic"]
        report_filter = schemas.SmartPayTrainingReportFilter(quiz_names=quiz_names)
        results = user_repo_with_data.get_user_quiz_completion_report(report_filter, 1)
        assert len(results) > 0  # Check that we get results back
        assert all(result.quiz in quiz_names for result in results)


def test_get_smartpay_training_report_with_filter_by_date_range(user_repo_with_data: UserRepository, agency_repo_with_data: AgencyRepository):
    """
    Test fetching report data with filters applied.
    """
    valid_agency = agency_repo_with_data.find_by_name(AgencyCreate(name="Department of Mysteries"))
    mock_user = UserSchemaFactory.build(roles=[])
    agency = Agency(id=valid_agency.id, name=valid_agency.name)
    mock_user.report_agencies.append(agency)

    # Mock the repo and RequireRole dependencies
    with patch('training.repositories.UserRepository.find_by_id', return_value=mock_user):

        start_date = datetime(2023, 1, 1)
        end_date = datetime(2024, 12, 31)
        report_filter = schemas.SmartPayTrainingReportFilter(completion_date_start=start_date, completion_date_end=end_date)
        results = user_repo_with_data.get_user_quiz_completion_report(report_filter, 1)
        assert len(results) > 0  # Check that we get results back
        for result in results:
            assert start_date <= result.completion_date <= end_date


def test_get_smartpay_training_report_with_no_report_agencies(user_repo_with_data: UserRepository):
    """
    Test fetching report data with no reporting agency for user
    """
    mock_user = UserSchemaFactory.build(roles=[])
    mock_user.report_agencies = []

    # Mock the repo and RequireRole dependencies
    with patch('training.repositories.UserRepository.find_by_id', return_value=mock_user):

        report_filter = schemas.SmartPayTrainingReportFilter()
        with pytest.raises(Exception):
            user_repo_with_data.get_user_quiz_completion_report(report_filter, 1)
