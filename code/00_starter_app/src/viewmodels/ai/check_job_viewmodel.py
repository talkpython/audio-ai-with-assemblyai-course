from typing import Optional

import bson
from starlette.requests import Request

from db.job import BackgroundJob, JobActions
from services import background_service
from viewmodels.shared.viewmodel_base import ViewModelBase


class CheckJobViewModel(ViewModelBase):
    def __init__(self, request: Request, job_id: bson.ObjectId):
        super().__init__(request)
        self.job_id: Optional[bson.ObjectId] = job_id
        self.job_name: Optional[str] = None
        self.job: Optional[BackgroundJob] = None
        self.job_action_text: Optional[str] = None
        self.completed_item_name: Optional[str] = None
        self.job_url: Optional[str] = None

    async def load(self) -> bool:
        self.job = await background_service.job_by_id(self.job_id)
        if self.job is None:
            return False

        match self.job.action:
            case JobActions.transcribe:
                self.job_name = 'Transcribing'
                self.job_action_text = 'View transcript'
                self.completed_item_name = 'transcript'
                self.job_url = f'/podcasts/transcript/{self.job.podcast_id}/episode/{self.job.episode_number}'
            case JobActions.summarize:
                self.job_name = 'Summarizing'
                self.job_action_text = 'Reload for summary'
                self.completed_item_name = 'summary'
                self.job_url = ''
            case JobActions.chat:
                self.job_name = 'Preparing chat'
                self.job_action_text = 'Start chatting'
                self.completed_item_name = 'chat'
                self.job_url = f'/podcasts/chat/{self.job.podcast_id}/episode/{self.job.episode_number}'
            case _:
                return False

        return True
