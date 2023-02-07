import json
from uuid import uuid4
from typing import Optional
from redis import Redis

from training.config import settings
from ..models import TempUser


redis = Redis()


class UserCache:
    '''
    Accessor methods for redis cache to create temp tokens associated
    with users.
    '''

    CACHE_TTL = settings.EMAIL_TOKEN_TTL

    def get(self, token: str) -> Optional[TempUser]:
        user = redis.get(token)
        if user:
            user = json.loads(user)
            return TempUser(**user)

    def set(self, user: TempUser) -> str:
        token = str(uuid4())
        user_str = json.dumps(user.dict())
        # try/except here
        redis.set(token, user_str)
        redis.expire(token, self.CACHE_TTL)
        return token

    def delete(self, token: str):
        redis.delete(token)
