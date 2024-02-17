import asyncio
import concurrent.futures
import datetime
import re
from typing import Optional, Any

import assemblyai
import assemblyai.lemur
from assemblyai import TranscriptStatus, LemurTaskResponse, LemurModel

from db.chat import ChatQA
from db.transcripts import (
    EpisodeTranscript,
    EpisodeTranscriptWords,
    EpisodeTranscriptSummary,
    EpisodeTranscriptProjection, TranscriptWord,
)
from services import podcast_service

regex_tlrd = re.compile('^Here is a [0-9]+ sentence .+:')
regex_moments = re.compile('^Here is a [0-9]+ bullet point .+:')


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
    t0 = datetime.datetime.now()

    # Step 1: Do we already have all we need?
    db_transcript = await full_transcript_for_episode(podcast_id, episode_number)
    if db_transcript and db_transcript.summary_tldr:
        return db_transcript

    # No TX? Make one
    if not db_transcript:
        print(f"No transcript yet, so let's make one for {podcast_id} {episode_number}")
        db_transcript = await worker_transcribe_episode(podcast_id, episode_number)

    # Step 2: Get the podcast and episode
    podcast = await podcast_service.podcast_by_id(podcast_id)
    episode = await podcast_service.episode_by_number(podcast_id, episode_number)

    if not podcast or not episode:
        raise Exception(f"No episode with podcast ID {podcast_id} and episode number {episode_number}")

    # Step 3: Use that info to create the 2 prompts
    subtitle_text = f' and it focuses on "{podcast.subtitle}". ' if podcast.subtitle else '. '
    prompt_base = ('You are an expert journalist. I need you to read the '
                   'transcript and summarize it for me. '
                   'Use the style of a tech reporter at ArsTechnica. '
                   f'This comes from the podcast entitled "{podcast.title}"' +
                   subtitle_text +
                   f'The title of this episode is "{episode.title}". '
                   )

    tldr_prompt = prompt_base + 'Your response should be a TLDR summary of around 5 to 8 sentences.'
    moments_prompt = prompt_base + 'Your response should be in the form of 10 bullet points.'

    # Step 4: Create transcript text.
    transcript: str = ' '.join(w.text for w in db_transcript.words)

    # Step 5: Send the request to LeMUR.
    # First for TL;DR, second for key moments
    # BTW, Lemur.task() is blocking...
    #
    # Please use
    # future = lemur_client.task_async(...)
    # resp = await run_future(future)
    #
    lemur_client = assemblyai.lemur.Lemur()

    print('Summarizing with LeMUR, TL;DR mode.')
    resp: LemurTaskResponse = lemur_client.task(
        tldr_prompt,
        final_model=LemurModel.basic,
        max_output_size=2000,
        temperature=0.25,
        input_text=transcript
    )
    db_transcript.summary_tldr = resp.response.strip()

    print('Summarizing with LeMUR, key moments mode.')
    resp: LemurTaskResponse = lemur_client.task(
        moments_prompt,
        final_model=LemurModel.basic,
        max_output_size=2000,
        temperature=0.25,
        input_text=transcript
    )
    db_transcript.summary_bullets = resp.response.strip()

    # Step 6: Remove LLM restatements at the start of the response:
    # Here is a 5 sentence summary of the key details from the transcript in the style of an ArsTechnica tech reporter:
    # Here is a 10 bullet point summary of the key details from the transcript in the style of an ArsTechnica tech reporter:.
    #
    db_transcript.summary_tldr = regex_tlrd.sub('', db_transcript.summary_tldr)
    db_transcript.summary_bullets = regex_moments.sub('', db_transcript.summary_bullets)

    await db_transcript.save()

    dt = datetime.datetime.now() - t0
    print(f'Processing complete for summary, dt = {dt.total_seconds():,.0f} sec.')


async def worker_enable_chat_episode(podcast_id: str, episode_number: int):
    print(f'Preparing episode for AI chat {podcast_id} and {episode_number}.')
    return await worker_transcribe_episode(podcast_id, episode_number)


async def ask_chat(podcast_id: str, episode_number: int, email: str, question: str) -> ChatQA:
    db_transcript = await full_transcript_for_episode(podcast_id, episode_number)
    if not db_transcript:
        raise Exception("Transcript required for chat.")

    podcast = await podcast_service.podcast_by_id(podcast_id)
    prompt = (f'You are an expert journalist. I am going to give you a transcript for the podcast "{podcast.title}". '
              'I want your answer to include sources and fragments from the transcript to support your response. '
              'I do not want you to make anything up. It\'s OK to say "I don\'t know." '
              ''
              f'My question about this podcast episode is:'
              '' +
              question)

    chat = await new_chat(podcast_id, episode_number, prompt, question, email)
    if chat.answer:
        return chat

    lemur_client = assemblyai.lemur.Lemur()

    print(f'Asking LeMUR about {question}')
    resp: LemurTaskResponse = lemur_client.task(
        prompt,
        final_model=LemurModel.basic,
        temperature=0.25,
        input_text=db_transcript.transcript_string
    )

    chat.answer = resp.response.strip()
    await chat.save()

    return chat


async def new_chat(podcast_id: str, episode_number: int, prompt: str, question: str, email: str) -> ChatQA:
    their_chat = await ChatQA.find_one(ChatQA.podcast_id == podcast_id,
                                       ChatQA.episode_number == episode_number,
                                       ChatQA.prompt == prompt,
                                       ChatQA.question == question,
                                       ChatQA.email == email)

    if their_chat is not None:
        return their_chat

    chat = ChatQA(podcast_id=podcast_id,
                  episode_number=episode_number,
                  prompt=prompt,
                  question=question,
                  email=email)

    existing_chat = await ChatQA.find_one(ChatQA.podcast_id == podcast_id,
                                          ChatQA.episode_number == episode_number,
                                          ChatQA.prompt == prompt,
                                          ChatQA.question == question)

    if existing_chat is not None and existing_chat.answer:
        chat.answer = existing_chat.answer

    await chat.save()
    return chat


async def run_future(future: concurrent.futures.Future) -> Any:
    while future.running():
        await asyncio.sleep(0.05)

    return future.result()
