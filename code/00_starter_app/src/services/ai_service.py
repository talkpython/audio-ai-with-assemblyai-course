import asyncio
import concurrent.futures
import datetime
from typing import Optional, Any

import assemblyai
from assemblyai import TranscriptionConfig, TranscriptStatus, LemurModel, LemurSummaryResponse

from db.transcripts import (
    EpisodeTranscript,
    TranscriptWord,
    EpisodeTranscriptWords,
    EpisodeTranscriptSummary,
    EpisodeTranscriptProjection,
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

    episode = await podcast_service.episode_by_number(podcast_id, episode_number)
    if episode is None:
        raise Exception(f'Cannot find episode {episode_number} from {podcast_id}.')

    db_transcript = await full_transcript_for_episode(podcast_id, episode_number)
    if db_transcript:
        print(f'Transcript for {podcast_id} number {episode_number} already exists, skipping.')
        return db_transcript

    print(f'Creating transcript for {episode.title} ...', flush=True)

    url = episode.enclosure_url

    # Ability to set the model coming soon

    transcriber = assemblyai.Transcriber()
    config = TranscriptionConfig(
        punctuate=True,
        format_text=True,
        disfluencies=False,
        speaker_labels=False,
    )

    transcript_future = transcriber.transcribe_async(url, config)
    transcript = await run_future(transcript_future)

    print(f'Transcript complete for {podcast_id}, number {episode_number}: {transcript.status} {transcript.error}')

    db_transcript = EpisodeTranscript(
        podcast_id=podcast_id,
        episode_number=episode_number,
        successful=transcript.status == TranscriptStatus.completed,
        status=transcript.status,
        assemblyai_id=transcript.id,
        json_result=transcript.json_response,
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
    print(f'Processing complete for transcribe, dt = {dt.total_seconds():,.3} sec.')

    return db_transcript


async def worker_summarize_episode(podcast_id: str, episode_number: int):
    t0 = datetime.datetime.now()

    episode = await podcast_service.episode_by_number(podcast_id, episode_number)
    if episode is None:
        raise Exception(f'Cannot find episode {episode_number} from {podcast_id}.')

    db_transcript = await full_transcript_for_episode(podcast_id, episode_number)
    if db_transcript and db_transcript.summary_bullets:
        print(f'Summary for {podcast_id} number {episode_number} already exists, skipping.')
        return

    if not db_transcript:
        print('No transcript for this episode, generating it now before summary...')
        db_transcript = await worker_transcribe_episode(podcast_id, episode_number)

    print(f'Creating summary for {episode.title} ...', flush=True)

    context = (
        'You are an expert journalist. I need you to read the transcript and summarize it for me. '
        'Use the style of a tech reporter at ArsTechnica. '
        'Your response should be a TLDR summary of around 5 to 8 sentences long.'
    )

    text = ' '.join([w.text for w in db_transcript.words])
    lemur = assemblyai.lemur.Lemur()

    resp: LemurSummaryResponse = lemur.summarize(
        context=context,
        answer_format='TLDR',
        final_model=LemurModel.basic,
        max_output_size=2000,
        temperature=0.25,
        input_text=text,
    )
    summary_tldr = resp.response

    context = (
        'You are an expert journalist. I need you to read the transcript and summarize it for me. '
        'Use the style of a tech reporter at ArsTechnica. '
        'Your response should be in the form of 10 bullet points.'
    )
    resp: LemurSummaryResponse = lemur.summarize(
        context=context,
        answer_format='bullet points verbose',
        final_model=LemurModel.basic,
        max_output_size=2000,
        temperature=0.25,
        input_text=text,
    )
    summary_bullets = resp.response

    db_transcript.successful = True
    db_transcript.summary_tldr = summary_tldr
    db_transcript.summary_bullets = summary_bullets

    print(f'Summary complete for {podcast_id}, number {episode_number}')

    if not db_transcript.successful:
        msg = (
            f'Error processing summary: {podcast_id} num {episode_number}: '
            f'{db_transcript.status} -> {db_transcript.error_msg}'
        )
        raise Exception(msg)

    db_transcript.updated_date = datetime.datetime.now()
    await db_transcript.save()

    dt = datetime.datetime.now() - t0
    print(f'Processing complete for summary, dt = {dt.total_seconds():,.3} sec.')

    return db_transcript


async def run_future(future: concurrent.futures.Future) -> Any:
    while future.running():
        await asyncio.sleep(0.05)

    return future.result()
