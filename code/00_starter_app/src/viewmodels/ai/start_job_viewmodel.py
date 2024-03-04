from typing import Optional

import bson
from starlette.requests import Request

from db.job import JobActions
from viewmodels.shared.viewmodel_base import ViewModelBase


class StartJobViewModel(ViewModelBase):
    def __init__(self, request: Request, podcast_id: str, episode_id: int, action: JobActions):
        super().__init__(request)
        self.action = action
        self.episode_id = episode_id
        self.podcast_id = podcast_id
        self.podcast_url: Optional[str] = None
        self.job_id: Optional[bson.ObjectId] = None
        self.job_name: Optional[str] = None
        self.job_action_text: Optional[str] = None
        self.completed_item_name: Optional[str] = None

        # match self.action:
        #     case JobActions.transcribe:
        #         self.job_name = 'Transcribing'
        #         self.job_action_text = 'View transcript'
        #     case JobActions.summarize:
        #         self.job_name = 'Summarizing'
        #         self.job_action_text = 'View summary'
        #     case JobActions.chat:
        #         self.job_name = 'Preparing chat'
        #         self.job_action_text = 'Start chatting'
        #     case _:
        #         raise Exception(f'Unsupported action type {action}')

        # Here is a Python 3.9 compatible version. If you are using 3.10 or later,
        # please prefer the above.
        if self.action == JobActions.transcribe:
            self.job_name = 'Transcribing'
            self.job_action_text = 'View transcript'
        elif self.action == JobActions.summarize:
            self.job_name = 'Summarizing'
            self.job_action_text = 'View summary'
        elif self.action == JobActions.chat:
            self.job_name = 'Preparing chat'
            self.job_action_text = 'Start chatting'
        else:
            raise Exception(f'Unsupported action type {action}')

    async def load(self) -> bool:
        pass
