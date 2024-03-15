import asyncio
import datetime
from typing import Optional

import bson

from db.job import BackgroundJob, JobStatus, JobActions
from services import podcast_service, ai_service


async def create_background_job(action: JobActions, podcast_id: str, episode_number: int) -> BackgroundJob:
    job = BackgroundJob(action=action, podcast_id=podcast_id, episode_number=episode_number)
    await job.save()

    return job


async def pending_jobs(limit=1_000) -> list[BackgroundJob]:
    try:
        return await (
            BackgroundJob.find(BackgroundJob.processing_status == JobStatus.awaiting)
            .sort('created_date')
            .limit(limit)
            .to_list()
        )
    except Exception as x:
        print(f'Error retrieving pending jobs: {x}')
        return []


async def start_job_processing(job_id: bson.ObjectId) -> Optional[BackgroundJob]:
    job = await job_by_id(job_id)
    if not job:
        raise Exception(f'No nob with that ID: {job_id}')

    if job.processing_status != JobStatus.awaiting:
        raise Exception(f'Cannot start job {job_id} with status {job.processing_status}.')

    job.processing_status = JobStatus.processing
    job.started_date = datetime.datetime.now()
    await job.save()

    return job


async def complete_job(job_id: bson.ObjectId, processing_status: JobStatus) -> Optional[BackgroundJob]:
    job = await job_by_id(job_id)
    if not job:
        raise Exception(f'No job with ID {job_id}.')

    if job.processing_status != JobStatus.processing:
        raise Exception(f'Cannot complete job {job_id} with status {job.processing_status}.')

    job.processing_status = processing_status
    job.is_finished = True
    job.finished_date = datetime.datetime.now()

    await job.save()

    return job


async def job_by_id(job_id: bson.ObjectId) -> Optional[BackgroundJob]:
    return await BackgroundJob.find_one(BackgroundJob.id == job_id)


async def is_job_finished(job_id: bson.ObjectId) -> bool:
    job: Optional[BackgroundJob] = await job_by_id(job_id)
    if not job:
        return False

    return job.is_finished


async def worker_function():
    print('Background asyncio service worker up and running.')
    await asyncio.sleep(1)

    while True:
        jobs = await pending_jobs(1)
        if not jobs:
            # print('No new jobs to process, chilling for now ...')
            await asyncio.sleep(1)
            continue

        job = jobs[0]
        try:
            await start_job_processing(job.id)
            print(f'Starting new job: {job.id}, {job.podcast_id} episode {job.episode_number}')
        except Exception as x:
            print(f'Error starting new job: {job.id}: {x}')
            continue

        try:
            episode = await podcast_service.episode_by_number(job.podcast_id, job.episode_number)
            if not episode:
                print(f'Error, cannot process job {job.id}, episode not found.')
                await complete_job(job.id, JobStatus.failed)
                continue
        except Exception as x:
            print(f'Error getting podcast details for job: j={job.id}, p={job.podcast_id}, e={job.episode_number}: {x}')

        try:
            # match job.action:
            #     case JobActions.summarize:
            #         await ai_service.worker_summarize_episode(job.podcast_id, job.episode_number)
            #     case JobActions.transcribe:
            #         await ai_service.worker_transcribe_episode(job.podcast_id, job.episode_number)
            #     case JobActions.chat:
            #         await ai_service.worker_enable_chat_episode(job.podcast_id, job.episode_number)
            #     case _:
            #         raise Exception(f'What am I supposed to do with {job.action}?')

            # Here is a Python 3.9 compatible version. If you are using 3.10 or later,
            # please prefer the above.
            if job.action == JobActions.summarize:
                await ai_service.worker_summarize_episode(job.podcast_id, job.episode_number)
            elif job.action == JobActions.transcribe:
                await ai_service.worker_transcribe_episode(job.podcast_id, job.episode_number)
            elif job.action == JobActions.chat:
                await ai_service.worker_enable_chat_episode(job.podcast_id, job.episode_number)
            else:
                raise Exception(f'What am I supposed to do with {job.action}?')

            await complete_job(job.id, JobStatus.success)
        except Exception as x:
            print(f'Error processing job {job.id} for {job.action}: {x}')
            await complete_job(job.id, JobStatus.failed)
