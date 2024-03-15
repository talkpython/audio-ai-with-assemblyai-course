import datetime
from typing import Optional

import beanie
import pydantic
import pymongo

# Switching to package strenum because enum.StrEnum didn't appear
# until Python 3.11. I don't want that high of a version requirement
# for you all. :)
#
# from enum import StrEnum
from strenum import StrEnum


class JobStatus(StrEnum):
    awaiting = 'awaiting'
    processing = 'processing'
    unneeded = 'unneeded'
    failed = 'failed'
    success = 'success'


class JobActions(StrEnum):
    transcribe = 'transcribe'
    summarize = 'summarize'
    chat = 'chat'


class BackgroundJob(beanie.Document):
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    started_date: Optional[datetime.datetime] = None
    finished_date: Optional[datetime.datetime] = None
    processing_status: str = JobStatus.awaiting
    is_finished: bool = False
    action: str
    episode_number: Optional[int] = None
    podcast_id: str

    class Settings:
        name = 'jobs'
        indexes = [
            # pymongo.IndexModel(keys=[('created_date', pymongo.ASCENDING)], name='created_date_ascend'),
            pymongo.IndexModel(keys=[('is_finished', pymongo.ASCENDING)], name='finished_ascend'),
            pymongo.IndexModel(keys=[('processing_status', pymongo.ASCENDING)], name='status_ascend'),
            pymongo.IndexModel(
                keys=[('podcast_id', pymongo.ASCENDING), ('episode_number', pymongo.ASCENDING)],
                name='podcast_and_episode_ascend',
            ),
            pymongo.IndexModel(
                keys=[
                    ('podcast_id', pymongo.ASCENDING),
                    ('episode_number', pymongo.ASCENDING),
                    ('processing_status', pymongo.ASCENDING),
                ],
                name='podcast_and_episode_status_ascend',
            ),
            # Do we want to expire and remove these docs? Probably.
            pymongo.IndexModel(
                keys=[('created_date', pymongo.ASCENDING)],
                name='created_date_expiring',
                expireAfterSeconds=int(datetime.timedelta(days=7).total_seconds()),
            ),
        ]
