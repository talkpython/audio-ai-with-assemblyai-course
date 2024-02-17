import asyncio
import concurrent.futures
from typing import Optional, Any

from db.transcripts import (
    EpisodeTranscript,
    EpisodeTranscriptWords,
    EpisodeTranscriptSummary,
    EpisodeTranscriptProjection,
)


async def full_transcript_for_episode(podcast_id: str, episode_number: int) -> Optional[EpisodeTranscript]:
    return await EpisodeTranscript.find_one(
        EpisodeTranscript.podcast_id == podcast_id, EpisodeTranscript.episode_number == episode_number
    )


async def summary_for_episode(podcast_id: str, episode_number: int) -> Optional[EpisodeTranscriptSummary]:
    summary = await EpisodeTranscript.find_one(
        EpisodeTranscript.podcast_id == podcast_id, EpisodeTranscript.episode_number == episode_number
    ).project(EpisodeTranscriptSummary)

    if summary is None or summary.summary_tldr is None:
        return None

    return summary


async def transcript_words_for_episode(podcast_id: str, episode_number: int) -> Optional[EpisodeTranscriptWords]:
    return await EpisodeTranscript.find_one(
        EpisodeTranscript.podcast_id == podcast_id, EpisodeTranscript.episode_number == episode_number
    ).project(EpisodeTranscriptWords)


async def transcript_lite_for_episode(podcast_id: str, episode_number: int) -> Optional[EpisodeTranscriptWords]:
    return await EpisodeTranscript.find_one(
        EpisodeTranscript.podcast_id == podcast_id, EpisodeTranscript.episode_number == episode_number
    ).project(EpisodeTranscriptProjection)


async def latest_transcript_for_podcast(podcast_id: str) -> Optional[EpisodeTranscript]:
    return (
        await EpisodeTranscript.find(EpisodeTranscript.podcast_id == podcast_id).sort('-created_date').first_or_none()
    )


async def worker_transcribe_episode(podcast_id: str, episode_number: int) -> EpisodeTranscript:
    # TODO: Actually transcribe episode at AssemblyAI
    return None


async def worker_summarize_episode(podcast_id: str, episode_number: int):
    # TODO: Actually summarize episode at AssemblyAI
    return None


async def worker_enable_chat_episode(podcast_id: str, episode_number: int):
    # TODO: Actually prepare chat for the episode at AssemblyAI
    return None


async def run_future(future: concurrent.futures.Future) -> Any:
    while future.running():
        await asyncio.sleep(0.05)

    return future.result()
