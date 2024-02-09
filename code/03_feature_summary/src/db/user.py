import datetime

import beanie
import pydantic
import pymongo


class User(beanie.Document):
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    last_login: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)

    name: str
    email: str
    password_hash: str
    is_admin: bool = False

    podcasts: list[str] = []

    class Settings:
        name = 'users'
        use_revision = False
        indexes = [
            pymongo.IndexModel(keys=[('created_date', pymongo.ASCENDING)], name='created_date_ascend'),
            pymongo.IndexModel(keys=[('last_updated', pymongo.DESCENDING)], name='last_updated_descending'),
            pymongo.IndexModel(keys=[('email', pymongo.ASCENDING)], name='email_ascend', unique=True),
            pymongo.IndexModel(keys=[('podcasts', pymongo.ASCENDING)], name='podcasts_ascend', unique=True),
        ]
