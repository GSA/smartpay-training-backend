from sqlalchemy import nullsfirst, or_
from sqlalchemy.orm import Session
from training import models, schemas
from training.schemas import UserQuizCompletionReportData, UserSearchResult, SmartPayTrainingReportFilter
from .base import BaseRepository
from datetime import datetime
from collections import namedtuple


class UserRepository(BaseRepository[models.User]):

    def __init__(self, session: Session):
        super().__init__(session, models.User)

    def create(self, user: schemas.UserCreate) -> models.User:
        return self.save(models.User(email=user.email.lower(), name=user.name, agency_id=user.agency_id, created_by=user.name))

    def find_by_email(self, email: str) -> models.User | None:
        return self._session.query(models.User).filter(models.User.email == email.lower()).first()

    def find_by_agency(self, agency_id: int) -> list[models.User]:
        return self._session.query(models.User).filter(models.User.agency_id == agency_id).all()

    def edit_user_for_reporting(self, user_id: int, report_agencies_list: list[int], modified_by: str) -> models.User:
        # edit_user_for_reporting allow admin to assign report role and associate report agencies to specific user
        db_user = self._session.query(models.User).filter(models.User.id == user_id).first()
        if db_user is None:
            raise ValueError("invalid user id")
        report_role_exist = [obj for obj in db_user.roles if obj.name == "Report"]
        if len(report_agencies_list) > 0:
            if len(report_role_exist) == 0:
                report_role = self._session.query(models.Role).filter(models.Role.name == "Report").first()
                if report_role:
                    db_user.roles.append(report_role)
                else:
                    # if Report role is not in DB, add it to DB (should not happen if data is prepopulated properly via seed.py and no direct DB removal)
                    role = models.Role(name="Report")
                    self._session.add(role)
                    self._session.commit()
                    db_user.roles.append(role)
        else:
            # if report_agencies_list =[], it will remove all user associated agencies and thus remove user report role.
            if len(report_role_exist) > 0:
                db_user.roles = [obj for obj in db_user.roles if obj.name != "Report"]
        db_user.report_agencies.clear()
        for agency_id in report_agencies_list:
            agency = self._session.query(models.Agency).filter(models.Agency.id == agency_id).first()
            if agency:
                db_user.report_agencies.append(agency)
            else:
                raise ValueError("invalid agency associated with this user")
        db_user.modified_by = modified_by
        db_user.modified_on = datetime.now()
        self._session.commit()
        return db_user

    def get_user_quiz_completion_report(self, filter: SmartPayTrainingReportFilter, report_user_id: int) -> list[UserQuizCompletionReportData]:
        report_data = namedtuple("ReportData", ["name", "email", "agency", "bureau", "quiz", "completion_date"])
        report_user = self.find_by_id(report_user_id)

        # Build the query
        query = (
            self._session.query(
                models.User.name,
                models.User.email,
                models.Agency.name,
                models.Agency.bureau,
                models.Quiz.name,
                models.QuizCompletion.submit_ts
            )
            .select_from(models.User)
            .join(models.Agency)
            .join(models.QuizCompletion)
            .join(models.Quiz)
            .filter(models.QuizCompletion.passed)
        )

        if report_user and report_user.report_agencies:
            # Dynamically add filters based on the properties of the SmartPayTrainingReportFilter
            if filter.bureau_id is not None:
                query = query.filter(models.User.agency_id == filter.bureau_id)
            elif filter.agency_id is not None:
                query = query.filter(models.User.agency_id == filter.agency_id)
            else:
                allowed_agency_ids = [obj.id for obj in report_user.report_agencies]
                query = query.filter(models.User.agency_id.in_(allowed_agency_ids))

            if filter.completion_date_start is not None:
                query = query.filter(models.QuizCompletion.submit_ts >= filter.completion_date_start)

            if filter.completion_date_end is not None:
                query = query.filter(models.QuizCompletion.submit_ts <= filter.completion_date_end)

            if filter.quiz_names:
                query = query.filter(models.Quiz.name.in_(filter.quiz_names))

            raw_results = query.order_by(
                models.Agency.name.asc(),
                nullsfirst(models.Agency.bureau.asc()),
                models.QuizCompletion.submit_ts.desc()
            ).all()

            # Map the results to the Pydantic model using the `ReportData` namedtuple
            result = [
                UserQuizCompletionReportData(
                    name=row.name,
                    email=row.email,
                    agency=row.agency,
                    bureau=row.bureau,
                    quiz=row.quiz,
                    completion_date=row.completion_date
                )
                for row in map(report_data._make, raw_results)
            ]

            return result
        else:
            raise ValueError("Invalid Report User")

    def get_admin_smartpay_training_report(self, filter: SmartPayTrainingReportFilter) -> list[UserQuizCompletionReportData]:
        report_data = namedtuple("ReportData", ["name", "email", "agency", "bureau", "quiz", "completion_date"])

        # Build the query
        query = (
            self._session.query(
                models.User.name,
                models.User.email,
                models.Agency.name,
                models.Agency.bureau,
                models.Quiz.name,
                models.QuizCompletion.submit_ts
            )
            .select_from(models.User)
            .join(models.Agency)
            .join(models.QuizCompletion)
            .join(models.Quiz)
            .filter(models.QuizCompletion.passed)
        )

        # Dynamically add filters based on the properties of the SmartPayTrainingReportFilter
        if filter.bureau_id is not None:
            query = query.filter(models.User.agency_id == filter.bureau_id)
        elif filter.agency_id is not None:
            query = query.filter(models.User.agency_id == filter.agency_id)

        if filter.completion_date_start is not None:
            query = query.filter(models.QuizCompletion.submit_ts >= filter.completion_date_start)

        if filter.completion_date_end is not None:
            query = query.filter(models.QuizCompletion.submit_ts <= filter.completion_date_end)

        if filter.quiz_names:
            query = query.filter(models.Quiz.name.in_(filter.quiz_names))

        raw_results = query.order_by(
            models.Agency.name.asc(),
            nullsfirst(models.Agency.bureau.asc()),
            models.QuizCompletion.submit_ts.desc()
        ).all()

        # Map the results to the Pydantic model using the `ReportData` namedtuple
        result = [
            UserQuizCompletionReportData(
                name=row.name,
                email=row.email,
                agency=row.agency,
                bureau=row.bureau,
                quiz=row.quiz,
                completion_date=row.completion_date
            )
            for row in map(report_data._make, raw_results)
        ]

        return result

    def get_users(self, searchText: str, page_number: int) -> UserSearchResult:
        # current UI only support search by user name and email. The search field it is required field.
        if (searchText and searchText.strip() != '' and page_number > 0):
            count = self._session.query(models.User).filter(or_(models.User.name.ilike(f"%{searchText}%"), models.User.email.ilike(f"%{searchText}%"))).count()
            page_size = 25
            offset = (page_number - 1) * page_size
            search_results = self._session.query(models.User).filter(
                or_(models.User.name.ilike(f"%{searchText}%"), models.User.email.ilike(f"%{searchText}%"))).limit(page_size).offset(offset).all()
            user_search_result = UserSearchResult(users=search_results, total_count=count)
            return user_search_result

    def update_user(self, user_id: int, user: schemas.UserUpdate, modified_by: str) -> models.User:
        """
        Updates user name and agency values
        :param user_id: User's ID to update
        :param user: User object with updated values
        :return: Updated User object
        """
        db_user = self.find_by_id(user_id)
        if db_user is None:
            raise ValueError("invalid user id")
        db_user.name = user.name
        db_user.agency_id = user.agency_id
        db_user.modified_by = modified_by
        db_user.modified_on = datetime.now()
        self._session.commit()
        return db_user
