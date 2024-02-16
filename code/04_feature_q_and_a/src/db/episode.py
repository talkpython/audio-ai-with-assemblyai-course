import datetime
from typing import Optional

import beanie
import pydantic
import pymongo


class Episode(beanie.Document):
    title: str
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    published_date: datetime.datetime
    episode_guid: str
    episode_number: Optional[int] = None
    episode_url: Optional[str] = None
    podcast_id: str

    enclosure_url: str
    enclosure_length_bytes: int
    enclosure_type: str

    summary: Optional[str] = None
    description: str
    tags: list[str] = []
    explicit: bool = False
    duration_in_sec: Optional[int] = None
    duration_text: Optional[str] = None

    class Settings:
        name = 'episodes'
        indexes = [
            pymongo.IndexModel(keys=[('created_date', pymongo.ASCENDING)], name='created_date_ascend'),
            pymongo.IndexModel(keys=[('episode_number', pymongo.DESCENDING)], name='episode_number_descend'),
            pymongo.IndexModel(keys=[('podcast_id', pymongo.ASCENDING)], name='podcast_id_ascend'),
            pymongo.IndexModel(keys=[('keywords', pymongo.ASCENDING)], name='keywords_ascend'),
            pymongo.IndexModel(keys=[('explicit', pymongo.ASCENDING)], name='explicit_ascend'),
            pymongo.IndexModel(keys=[
                ('podcast_id', pymongo.ASCENDING),
                ('episode_number', pymongo.ASCENDING),
            ], name='podcast_id__episode_number_ascend'),
            pymongo.IndexModel(keys=[
                ('podcast_id', pymongo.ASCENDING),
                ('episode_number', pymongo.DESCENDING),
            ], name='podcast_id__episode_number_descend'),

        ]


class EpisodeLightProjection(pydantic.BaseModel):
    title: str
    summary: Optional[str] = None
    published_date: datetime.datetime
    episode_number: Optional[int] = None
    podcast_id: str
