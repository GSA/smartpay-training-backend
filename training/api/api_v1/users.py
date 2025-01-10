import csv
from io import StringIO
import logging
from training.api.auth import RequireRole
from fastapi import APIRouter, status, HTTPException, Response, Depends, Query
from training.schemas import User, UserCreate, UserSearchResult, UserUpdate, SmartPayTrainingReportFilter
from training.repositories import UserRepository
from training.api.deps import user_repository
from typing import Annotated


router = APIRouter()


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
        new_user: UserCreate,
        repo: UserRepository = Depends(user_repository),
        user=Depends(RequireRole(["Admin"]))
):
    db_user = repo.find_by_email(new_user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email address already exists"
        )
    db_user = repo.create(user)
    logging.info(f"{user['email']} created user {new_user.email}")
    return db_user


@router.patch("/users/edit-user-for-reporting", response_model=User)
def edit_user_for_reporting(
        user_id: int,
        agency_id_list: list[int],
        repo: UserRepository = Depends(user_repository),
        user=Depends(RequireRole(["Admin"]))
):
    try:
        updated_user = repo.edit_user_for_reporting(user_id, agency_id_list, user['name'])
        logging.info(f"{user['email']} granted user {updated_user.email} reporting for agencies: {agency_id_list}")
        return User.model_validate(updated_user)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid user id or agencies ids"
        )


@router.post("/users/download-smartpay-training-report")
def download_smartpay_training_report_csv(
        filter_info: SmartPayTrainingReportFilter,
        repo: UserRepository = Depends(user_repository),
        user=Depends(RequireRole(["Report"]))
):
    '''
    :param filter_info: filter parameters
    :param repo: User Repository
    :param user: User
    :return: Returns a report of all quiz_completions based on the pasted in filter_info.
    '''
    try:
        results = repo.get_user_quiz_completion_report(filter_info, user['id'])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to process"
        )

    output = StringIO()
    writer = csv.writer(output)

    # header row
    writer.writerow(['Full Name', 'Email Address', 'Agency', 'Bureau', 'Quiz Name', 'Quiz Completion Date and Time'])
    for item in results:
        # data row
        writer.writerow([item.name, item.email, item.agency, item.bureau, item.quiz, item.completion_date.strftime("%m/%d/%Y %H:%M:%S")])  # noqa 501

    headers = {'Content-Disposition': 'attachment; filename="SmartPayTrainingQuizCompletionReport.csv"'}
    return Response(output.getvalue(), headers=headers, media_type='application/csv')


@router.post("/users/download-admin-smartpay-training-report")
def download_admin_smartpay_training_report_csv(
    filter_info: SmartPayTrainingReportFilter,
    repo: UserRepository = Depends(user_repository),
    user=Depends(RequireRole(["Admin"])
                 )):
    '''
    Returns a report of all quiz_completions based on the pasted in filter_info.
    '''
    try:
        results = repo.get_admin_smartpay_training_report(filter_info)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to process"
        )
    output = StringIO()
    writer = csv.writer(output)

    # header row
    writer.writerow(['Full Name', 'Email Address', 'Agency', 'Bureau', 'Quiz Name', 'Quiz Completion Date and Time'])
    for item in results:
        # data row
        writer.writerow([item.name, item.email, item.agency, item.bureau, item.quiz, item.completion_date.strftime("%m/%d/%Y %H:%M:%S")])  # noqa 501

    headers = {'Content-Disposition': 'attachment; filename="SmartPayTrainingReport.csv"'}
    return Response(output.getvalue(), headers=headers, media_type='application/csv')


@router.get("/users", response_model=UserSearchResult)
def get_users(
        searchText: Annotated[str, Query(min_length=1)],
        page_number: int = 1,
        repo: UserRepository = Depends(user_repository),
        user=Depends(RequireRole(["Admin"]))
):
    '''
    Get/users is used to search users for admin portal
    currently search only support search by user name and email address, searchText is required field.
    It may have additional search criteria in future, which will require logic update.
    page_number param is used to support UI pagination functionality.
    It returns UserSearchResult object with a list of users and total_count used for UI pagination
    '''
    return repo.get_users(searchText, page_number)


@router.get("/users/{user_id}", response_model=User)
def get_user(
        user_id: int,
        repo: UserRepository = Depends(user_repository),
        user=Depends(RequireRole(["Admin"]))
):
    '''
    Get/user is used to refresh user after edits for admin portal
    It returns a User object
    '''

    return repo.find_by_id(user_id)


@router.patch("/users/{user_id}", response_model=User)
def update_user_by_id(
        user_id: int,
        updated_user: UserUpdate,
        repo: UserRepository = Depends(user_repository),
        user=Depends(RequireRole(["Admin"]))
):
    """
    Updates user details by User ID
    :param updated_user: Updated user model
    :param user_id: User ID
    :param repo: UserRepository repository
    :param user: Required role to complete operation
    :return: Returns the updated user object
    """
    if user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can not update your own profile"
        )
    try:
        logging.info(f"{user['email']} updated user {updated_user.email} user profile")
        db_user = repo.update_user(user_id, updated_user, user["name"])
        return User.model_validate(db_user)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid user id"
        )
