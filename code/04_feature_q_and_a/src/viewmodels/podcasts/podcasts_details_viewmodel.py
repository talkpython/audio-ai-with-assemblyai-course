from typing import Optional

from starlette.requests import Request

from db.episode import EpisodeLightProjection
from db.podcast import Podcast
from services import podcast_service
from viewmodels.shared.viewmodel_base import ViewModelBase


def shorten_text(text: str, max_len: int) -> str:
    if not text or len(text) < max_len:
        return text

    final_text = text[: max_len - 5] + ' ...'
    return final_text


class PodcastDetailsViewModel(ViewModelBase):
    def __init__(self, request: Request, podcast_id: str):
        super().__init__(request)
        self.podcast_id: str = podcast_id
        self.podcast: Optional[Podcast] = None
        self.user_podcasts: list[Podcast] = []
        self.episodes: list[EpisodeLightProjection] = []
        self.shorten_text = shorten_text

    async def load_data(self):
        if self.user_id and not self.user:
            await self.load_user()

        podcast_ids = []
        if self.user:
            podcast_ids = self.user.podcasts

        self.user_podcasts = await podcast_service.podcasts_for_ids(podcast_ids)
        self.podcast = await podcast_service.podcast_by_id(self.podcast_id)
        if self.podcast:
            self.episodes = await podcast_service.episodes_for_podcast_light(self.podcast)
