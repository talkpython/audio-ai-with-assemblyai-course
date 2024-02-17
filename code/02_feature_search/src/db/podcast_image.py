import datetime
from typing import Optional

import beanie
import pydantic
import pymongo


class PodcastImage(beanie.Document):
    podcast_id: str
    image_url: str
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    content: bytes

    class Settings:
        name = 'podcast_images'
        indexes = [
            pymongo.IndexModel(keys=[('podcast_id', pymongo.ASCENDING)], name='podcast_id_ascend'),
            pymongo.IndexModel(
                keys=[('created_date', pymongo.ASCENDING)],
                name='created_date_expires',
                expireAfterSeconds=int(datetime.timedelta(days=7).total_seconds()),
            ),
        ]
