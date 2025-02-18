from typing import Any, Generic, List, Type, TypeVar
from sqlalchemy.orm import Session
from training import models


T = TypeVar("T", bound=models.Base)


class BaseRepository(Generic[T]):

    def __init__(self, session: Session, model: Type[T]):
        self._session = session
        self._model = model

    def save(self, item: T) -> T:
        self._session.add(item)
        self._session.commit()
        self._session.refresh(item)
        return item

    def bulk_save(self, items: List[T]) -> List[T]:
        """Bulk saves multiple items efficiently."""
        self._session.add_all(items)
        self._session.commit()

        for item in items:
            self._session.refresh(item)

        return items

    def find_by_id(self, id: int) -> T | None:
        return self._session.query(self._model).filter_by(id=id).first()

    def find_all(self, filters: dict[str, Any] = {}) -> list[T]:
        query = self._session.query(self._model)
        for key, value in filters.items():
            query = query.filter(getattr(self._model, key) == value)
        return query.all()

    def delete_by_id(self, id: int) -> None:
        self._session.query(self._model).filter_by(id=id).delete()
