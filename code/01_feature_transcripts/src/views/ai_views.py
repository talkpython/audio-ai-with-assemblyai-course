import bson
import fastapi
import fastapi_chameleon
from starlette.requests import Request

from db.job import JobActions
from infrastructure import webutils
from services import background_service
from viewmodels.ai.check_job_viewmodel import CheckJobViewModel
from viewmodels.ai.start_job_viewmodel import StartJobViewModel

router = fastapi.APIRouter()


@router.get('/ai/start/{action}/{podcast_id}/episode/{episode_number}')
@fastapi_chameleon.template('ai/job_running.html')
async def start_job(request: Request, action: JobActions, podcast_id: str, episode_number: int):
    vm = StartJobViewModel(request, podcast_id, episode_number, action)
    job = await background_service.create_background_job(action, podcast_id, episode_number)
    vm.job_id = job.id

    return vm.to_dict()


@router.get('/ai/check-status/{job_id}')
@fastapi_chameleon.template('ai/job_completed.html')
async def check_job_status(request: Request, job_id: str):
    vm = CheckJobViewModel(request, bson.ObjectId(job_id))
    if not await vm.load():
        return webutils.return_error('Could not load job details', status_code=500)

    if not vm.job.is_finished:
        print(f"The job {vm.job.id} is still running...")
        return fastapi_chameleon.response('ai/job_running.html', **vm.to_dict())

    return vm.to_dict()
