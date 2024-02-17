import asyncio
import concurrent.futures
import datetime
from typing import Optional, Any

import assemblyai
from assemblyai import TranscriptStatus

from db.transcripts import (
    EpisodeTranscript,
    EpisodeTranscriptWords,
    EpisodeTranscriptSummary,
    EpisodeTranscriptProjection, TranscriptWord,
)
from services import podcast_service


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
    t0 = datetime.datetime.now()

    db_transcript = await full_transcript_for_episode(podcast_id, episode_number)
    if db_transcript:
        print(f'Transcript for {podcast_id} number {episode_number} already exists, skipping.')
        return db_transcript

    podcast = await podcast_service.podcast_by_id(podcast_id)
    if not podcast:
        raise Exception(f"Podcast not found for ID {podcast_id}")

    episode = await podcast_service.episode_by_number(podcast_id, episode_number)
    if not episode:
        raise Exception(f"Episode not found for podcast {podcast_id} and episode {episode_number}")

    mp3_url = episode.enclosure_url
    print(f"We are transcribing {podcast.title} - {episode.title} from {mp3_url} ...")

    transcriber = assemblyai.Transcriber()
    config = assemblyai.TranscriptionConfig(
        punctuate=True,
        format_text=True,
        speaker_labels=False,
        disfluencies=False
    )

    transcript_future = transcriber.transcribe_async(mp3_url, config)
    transcript: assemblyai.Transcript = await run_future(transcript_future)

    db_transcript = EpisodeTranscript(
        episode_number=episode_number,
        podcast_id=podcast_id,
        successful=transcript.status == TranscriptStatus.completed,
        status=transcript.status,
        assemblyai_id=transcript.id,
        json_result=transcript.json_response
    )

    if not db_transcript.successful:
        msg = (
            f'Error processing transcript: {podcast_id} num {episode_number}: '
            f'{db_transcript.status} -> {db_transcript.error_msg or ""}'
        )
        raise Exception(msg)

    for word in transcript.words:
        start_sec = word.start / 1000.0
        tx_word = TranscriptWord(text=word.text, start_in_sec=start_sec, confidence=word.confidence)
        db_transcript.words.append(tx_word)

    await db_transcript.save()

    dt = datetime.datetime.now() - t0
    print(f'Processing complete for transcription, dt = {dt.total_seconds():,.0f} sec.')

    return db_transcript


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
