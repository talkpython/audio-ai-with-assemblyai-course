import re
from typing import Optional

from starlette.requests import Request

from db.episode import Episode
from db.podcast import Podcast
from services import podcast_service
from viewmodels.shared.viewmodel_base import ViewModelBase

regexs = [
    re.compile(r"^Based on the transcript provided, "),
    re.compile(r"^Based on the transcripts provided, "),
    re.compile(r"^Based on the transcript summary provided, "),
]


class EpisodeChatViewModel(ViewModelBase):
    def __init__(self, request: Request, podcast_id: str, episode_number: int):
        super().__init__(request)
        self.episode_number: int = episode_number
        self.podcast_id: str = podcast_id
        self.podcast: Optional[Podcast] = None
        self.episode: Optional[Episode] = None
        self.question: Optional[str] = None
        self.answer: Optional[str] = None

    async def load_data(self):
        if self.user_id and not self.user:
            await self.load_user()

        self.podcast = await podcast_service.podcast_by_id(self.podcast_id)
        self.episode = await podcast_service.episode_by_number(self.podcast_id, self.episode_number)

        if not self.user:
            self.error = "No user, cannot chat without having an account."
            return

        form = await self.request.form()
        if form:
            self.question = (form.get('question') or '').strip()

        if not self.question or not self.question.strip():
            self.error = "You gotta ask a question to make this magic happen."

    def set_answer(self, answer_text: str):
        self.answer = answer_text

        if self.answer:
            for regex in regexs:
                self.answer = regex.sub('', self.answer).strip()

            if not self.answer[0].isupper():
                self.answer = self.answer[0].upper() + self.answer[1:]

            # while '\n\n' in self.answer:
            #     self.answer = self.answer.replace('\n\n', '\n')

            self.answer = self.answer.replace("\n", "<br>\n")
