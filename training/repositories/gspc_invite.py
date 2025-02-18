from itertools import islice
from typing import Iterator, List
import uuid
from sqlalchemy.orm import Session
from training import models
from datetime import datetime, date
from .base import BaseRepository
import time


class GspcInviteRepository(BaseRepository[models.GspcInvite]):

    def __init__(self, session: Session):
        super().__init__(session, models.GspcInvite)

    def create(self, email: str, certification_expiration_date: date) -> models.GspcInvite:
        return self.save(models.GspcInvite(
            email=email,
            certification_expiration_date=certification_expiration_date,
            gspc_invite_id=uuid.uuid4()
        ))

    def bulk_create(self, emails: list[str], certification_expiration_date: date) -> list[models.GspcInvite]:
        """Bulk insert GspcInvite records for multiple emails."""
        invites = [
            models.GspcInvite(
                email=email,
                certification_expiration_date=certification_expiration_date,
                gspc_invite_id=uuid.uuid4()
            )
            for email in emails
        ]

        try:
            # Insert 50 at a time
            for batch in self.batch_iterator(invites, 50):
                self.bulk_save(batch)
                time.sleep(1)

            return invites

        except Exception as e:
            raise Exception(f"Batch insert failed: {str(e)}") from e

    def batch_iterator(items: List, batch_size: int) -> Iterator:
        """Create an iterator that yields batches of the specified size."""
        iterator = iter(items)
        batch = list(islice(iterator, batch_size))
        while batch:
            yield batch
            batch = list(islice(iterator, batch_size))

    def get_by_gspc_invite_id(self, gspc_invite_id: uuid.UUID) -> models.GspcInvite:
        """
        retrieves a GspcInvite by its gspc_invite_id
        param gspc_invite_id: (uuid.UUID): The UUID tied to each invite
        returns:models.GspcInvite: The matching invite record
        """
        result = self._session.query(models.GspcInvite).filter(
            models.GspcInvite.gspc_invite_id == gspc_invite_id
        ).first()

        if result is None:
            raise ValueError("No invite found with the given gspc_invite_id")
        return result

    def set_second_invite_date(self, id: int) -> None:
        """
        Sets second_invite_date to now
        :param id: gspc_invite ID to update
        :return: None
        """
        gspc_invite = self.find_by_id(id)
        if gspc_invite is None:
            raise ValueError("invalid gspc invite id")
        gspc_invite.second_invite_date = datetime.now()
        self._session.commit()

    def set_final_invite_date(self, id: int) -> None:
        """
        Sets final_invite_date to now
        :param id: gspc_invite ID to update
        :return: None
        """
        gspc_invite = self.find_by_id(id)
        if gspc_invite is None:
            raise ValueError("invalid gspc invite id")
        gspc_invite.final_invite_date = datetime.now()
        self._session.commit()

    def set_completion_date(self, id: int) -> None:
        """
        Sets completed_date to now
        :param id: gspc_invite ID to update
        :return: None
        """
        gspc_invite = self.find_by_id(id)
        if gspc_invite is None:
            raise ValueError("invalid gspc invite id")
        gspc_invite.completed_date = datetime.now()
        self._session.commit()
