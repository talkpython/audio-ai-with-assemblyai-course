import datetime
from typing import Optional

from starlette.requests import Request

from db.episode import EpisodeLightProjection
from db.podcast import Podcast
from services import search_service
from viewmodels.shared.viewmodel_base import ViewModelBase


class SearchResultsViewModel(ViewModelBase):
    def __init__(self, request: Request, search_text: Optional[str]):
        super().__init__(request)
        self.search_text: Optional[str] = search_text
        self.episodes: list[EpisodeLightProjection] = []
        self.podcasts: list[Podcast] = []
        self.podcast_lookup: dict[str, Podcast] = {}
        self.elapsed_time: float = 0.0

    async def load(self):
        if not self.search_text:
            return

        t0 = datetime.datetime.now()
        raw_search = await search_service.search(self.search_text)
        self.episodes = raw_search.episodes
        self.podcasts = raw_search.podcasts
        self.podcast_lookup = {p.id: p for p in self.podcasts}

        dt = datetime.datetime.now() - t0
        self.elapsed_time = dt.total_seconds()
