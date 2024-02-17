import datetime
from typing import Optional

import beanie
import pydantic
import pymongo
from assemblyai import TranscriptStatus


class TranscriptWord(pydantic.BaseModel):
    text: str
    start_in_sec: float
    confidence: float


class EpisodeTranscript(beanie.Document):
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    updated_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    episode_number: Optional[int] = None
    podcast_id: str

    words: list[TranscriptWord] = []

    summary_tldr: Optional[str] = None
    summary_bullets: Optional[str] = None

    error_msg: Optional[str] = None
    successful: bool
    status: TranscriptStatus
    assemblyai_id: str
    json_result: dict

    class Settings:
        name = 'transcripts'
        use_revision = False
        indexes = [
            pymongo.IndexModel(keys=[('created_date', pymongo.ASCENDING)], name='created_date_ascend'),
            pymongo.IndexModel(keys=[('episode_number', pymongo.DESCENDING)], name='episode_number_descend'),
            pymongo.IndexModel(keys=[('podcast_id', pymongo.ASCENDING)], name='podcast_id_ascend'),
            pymongo.IndexModel(keys=[('assemblyai_id', pymongo.ASCENDING)], name='assemblyai_id_ascend'),
            pymongo.IndexModel(
                keys=[('podcast_id', pymongo.ASCENDING), ('episode_number', pymongo.ASCENDING)],
                name='podcast_and_episode_ascend',
            ),
        ]

    @property
    def transcript_string(self) -> str:
        return ' '.join([w.text for w in self.words])


class EpisodeTranscriptProjection(pydantic.BaseModel):
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    updated_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    episode_number: Optional[int] = None
    podcast_id: str
    error_msg: Optional[str] = None
    successful: bool
    assemblyai_id: str


class EpisodeTranscriptWords(EpisodeTranscriptProjection):
    words: list[TranscriptWord] = []


class EpisodeTranscriptSummary(EpisodeTranscriptProjection):
    summary_tldr: Optional[str] = None
    summary_bullets: Optional[str] = None
