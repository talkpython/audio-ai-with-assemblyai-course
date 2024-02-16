from typing import Optional

from starlette.requests import Request

from db.episode import Episode
from db.podcast import Podcast
from db.transcripts import EpisodeTranscriptSummary
from services import podcast_service, ai_service, transcript_service
from services.transcript_service import Sentence
from viewmodels.shared.viewmodel_base import ViewModelBase


class PodcastEpisodeViewModel(ViewModelBase):
    def __init__(self, request: Request, podcast_id: str, episode_number: int):
        super().__init__(request)
        self.episode_number: int = episode_number
        self.podcast_id: str = podcast_id
        self.podcast: Optional[Podcast] = None
        self.episode: Optional[Episode] = None

        self.transcript_sentences: list[Sentence] = []
        self.ai_summary: Optional[EpisodeTranscriptSummary] = None

        self.transcript_url: Optional[str] = None
        self.summary_url: Optional[str] = None
        self.to_time_text = self.seconds_to_time_text
        self.summary_to_html = self.summary_to_html_converter

    async def load_data(self):
        if self.user_id and not self.user:
            await self.load_user()

        self.podcast = await podcast_service.podcast_by_id(self.podcast_id)
        self.episode = await podcast_service.episode_by_number(self.podcast_id, self.episode_number)
        self.ai_summary = await ai_service.summary_for_episode(self.podcast_id, self.episode_number)
        self.transcript_sentences = await transcript_service.transcript_text_for_episode(
            self.podcast_id, self.episode_number
        )

        tx_url = f'/podcasts/transcript/{self.podcast_id}/episode/{self.episode_number}'
        self.transcript_url = None if not self.transcript_sentences else tx_url

        summary_url = f'/podcasts/summary/{self.podcast_id}/episode/{self.episode_number}'
        self.summary_url = None if not self.ai_summary else summary_url

    @classmethod
    def seconds_to_time_text(cls, total_seconds: float) -> str:
        if total_seconds is None:
            return ''

        total_seconds = int(total_seconds)

        seconds = int(total_seconds) % 60
        minutes = int(total_seconds / 60) % 60
        hours = int(total_seconds / 60 / 60) % 24

        if hours:
            return f'{str(hours).zfill(2)}:{str(minutes).zfill(2)}:{str(seconds).zfill(2)}'
        if minutes:
            return f'{str(minutes).zfill(2)}:{str(seconds).zfill(2)}'

        return f'00:{str(seconds).zfill(2)}'

    def summary_to_html_converter(self):
        if not self.ai_summary:
            return ''

        html = ''
        html += '<h2>TL;DR</h2>\n\n'
        elements = self.ai_summary.summary_tldr.split('\n')
        for e in elements:
            if not e.strip():
                continue

            html += e + '<br>\n'
        html += '<br>'
        html += '<h2>Key Moments</h2>\n\n'
        html += '<ul>\n'
        elements = self.ai_summary.summary_bullets.split('\n')
        for e in elements:
            text = e.lstrip('-').lstrip('- ').strip()
            if text:
                if text[-1] not in {'.', '?', '!'}:
                    text += '.'
                html += f'<li>{text}</li>\n'

        html += '</ul>\n\n'

        return html
