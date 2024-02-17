import datetime
from typing import Optional

import beanie
import pydantic
import pymongo


class ChatQA(beanie.Document):
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    prompt: str
    question: str
    answer: Optional[str] = None

    email: str
    podcast_id: str
    episode_number: int = None

    class Settings:
        name = 'chat_history'
        indexes = [
            pymongo.IndexModel(keys=[('created_date', pymongo.ASCENDING)], name='created_date_ascend'),
            pymongo.IndexModel(keys=[('episode_number', pymongo.DESCENDING)], name='episode_number_descend'),
            pymongo.IndexModel(keys=[('podcast_id', pymongo.ASCENDING)], name='podcast_id_ascend'),
            pymongo.IndexModel(keys=[('email', pymongo.ASCENDING)], name='email_ascend'),
            pymongo.IndexModel(keys=[
                ('podcast_id', pymongo.ASCENDING),
                ('episode_number', pymongo.ASCENDING),
            ], name='podcast_id__episode_number_ascend'),
            pymongo.IndexModel(keys=[
                ('podcast_id', pymongo.ASCENDING),
                ('episode_number', pymongo.DESCENDING),
            ], name='podcast_id__episode_number_descend'),

        ]
