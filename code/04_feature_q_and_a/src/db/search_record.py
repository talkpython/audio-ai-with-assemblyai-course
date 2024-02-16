import datetime
from typing import Optional

import beanie
import pydantic
import pymongo
from beanie import PydanticObjectId


class SearchRecord(beanie.Document):
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    episode_date: Optional[datetime.datetime] = None
    episode_id: Optional[PydanticObjectId] = None
    episode_number: Optional[int] = None
    podcast_id: str

    keywords: set[str]

    class Settings:
        name = 'search_records'
        indexes = [
            pymongo.IndexModel(keys=[('keywords', pymongo.ASCENDING)], name='keywords_ascend'),
            pymongo.IndexModel(keys=[('created_date', pymongo.ASCENDING)], name='created_date_ascend'),
            pymongo.IndexModel(keys=[('episode_id', pymongo.DESCENDING)], name='episode_id_descend'),
            pymongo.IndexModel(keys=[('episode_number', pymongo.DESCENDING)], name='episode_number_descend'),
            pymongo.IndexModel(keys=[('episode_date', pymongo.DESCENDING)], name='episode_date_descend'),
            pymongo.IndexModel(keys=[('podcast_id', pymongo.ASCENDING)], name='podcast_id_ascend'),
            pymongo.IndexModel(
                keys=[('podcast_id', pymongo.ASCENDING), ('episode_number', pymongo.DESCENDING)],
                name='podcast_and_episode_descend',
            ),
        ]


class SearchRecordLite(pydantic.BaseModel):
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    episode_date: Optional[datetime.datetime] = None
    episode_id: Optional[PydanticObjectId] = None
    episode_number: Optional[int] = None
    podcast_id: str
