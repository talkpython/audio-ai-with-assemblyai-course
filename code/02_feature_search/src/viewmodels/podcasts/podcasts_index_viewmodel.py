from starlette.requests import Request

from db.podcast import Podcast
from services import podcast_service
from viewmodels.shared.viewmodel_base import ViewModelBase


class PodcastIndexViewModel(ViewModelBase):
    def __init__(self, request: Request):
        super().__init__(request)
        self.user_podcasts: list[Podcast] = []
        self.additional_podcasts: list[Podcast] = []

    async def load_data(self):

        if self.user_id and not self.user:
            await self.load_user()

        podcast_ids = []
        if self.user:
            podcast_ids = self.user.podcasts

        self.user_podcasts = await podcast_service.podcasts_for_ids(podcast_ids)

        popular_ids = {'talk-python-to-me', 'python-bytes', 'darknet-diaries'}
        self.additional_podcasts = [
            pod for pod in await podcast_service.all_podcast(limit=100) if pod.id not in popular_ids
        ]
