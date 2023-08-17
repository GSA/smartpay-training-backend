import csv
from io import StringIO
import logging
from training.api.auth import RequireRole
from fastapi import APIRouter, status, HTTPException, Response, Depends, Query
from training.schemas import User, UserCreate, UserSearchResult
from training.repositories import UserRepository
from training.api.deps import user_repository
from training.api.auth import user_from_form
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
        updated_user = repo.edit_user_for_reporting(user_id, agency_id_list)
        logging.info(f"{user['email']} granted user {updated_user.email} reporting for agencies: {agency_id_list}")
        return updated_user
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid user id or agencies ids"
        )


@router.post("/users/download-user-quiz-completion-report")
def download_report_csv(user=Depends(user_from_form), repo: UserRepository = Depends(user_repository)):
    try:
        results = repo.get_user_quiz_completion_report(user['id'])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid report user"
        )

    output = StringIO()
    writer = csv.writer(output)

    # header row
    writer.writerow(['Full Name', 'Email Address', 'Agency', 'Bureau', 'Quiz Name', 'Quiz Completion Date'])
    for item in results:
        # data row
        writer.writerow([item.name, item.email, item.agency, item.bureau, item.quiz, item.completion_date.strftime("%m/%d/%Y")])  # noqa 501

    headers = {'Content-Disposition': 'attachment; filename="SmartPayTrainingQuizCompletionReport.csv"'}
    return Response(output.getvalue(), headers=headers, media_type='application/csv')


@router.get("/users", response_model=UserSearchResult)
def get_users(
    name: Annotated[str, Query(min_length=1)],
    page_number: int = 1,
    repo: UserRepository = Depends(user_repository)#,
    #user=Depends(RequireRole(["Admin"]))
):
    '''
    Get/users is used to search users for admin portal
    currently search only support search by user name, name is required field.
    It may have additional search criteira in future, which will require logic update.
    page_number param is used to support UI pagination functionality.
    It returns UserSearchResult object with a list of users and total_count used for UI pagination
    '''
    return repo.get_users(name, page_number)
