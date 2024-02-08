from typing import Optional

from starlette.requests import Request

from db.podcast import Podcast
from services import podcast_service
from viewmodels.shared.viewmodel_base import ViewModelBase


class FollowPodcastViewModel(ViewModelBase):
    def __init__(self, request: Request):
        super().__init__(request)
        self.podcast_url: Optional[str] = None
        self.additional_podcasts: list[Podcast] = []

    async def load(self) -> bool:
        if not self.user:
            await self.load_user()

        popular_ids = {'talk-python-to-me', 'python-bytes', 'darknet-diaries'}
        self.additional_podcasts = [
            pod for pod in await podcast_service.all_podcast(limit=100) if pod.id not in popular_ids
        ]

        form = await self.request.form()
        self.podcast_url = (form.get('podcast_url') or '').strip()

        if not self.podcast_url:
            self.error = 'A podcast URL is required.'
            return False

        return not self.error
