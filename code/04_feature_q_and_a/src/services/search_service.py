import asyncio
import datetime
from typing import Optional, Tuple

import html2text
import pydantic
import spacy
from spacy import Language

from db.episode import EpisodeLightProjection
from db.podcast import Podcast
from db.search_record import SearchRecord, SearchRecordLite
from db.transcripts import EpisodeTranscript
from services import podcast_service, ai_service

indexing_startup = 5  # delay 30s
indexing_frequency = 60  # 60 * 5  # every 5 minutes

nlp: Optional[Language] = None


class RawSearchResult(pydantic.BaseModel):
    podcasts: list[Podcast] = []
    episodes: list[EpisodeLightProjection] = []


def manually_trigger_index_build():
    try:
        # noinspection PyAsyncCall
        asyncio.create_task(build_index_core())
    except Exception as x:
        print(f'!!! ERROR running search index: {x}')


async def search(search_text: str) -> RawSearchResult:
    search_enabled = nlp is not None

    if not search_enabled:
        print('Search not enabled!')
        return RawSearchResult()

    searchable_words = build_keywords(search_text)

    raw_result = await search_episodes(searchable_words)
    return raw_result


async def search_episodes(searchable_words: set[str]) -> RawSearchResult:
    if not searchable_words:
        return RawSearchResult()

    words = list(searchable_words)
    word1 = words[0]
    query = SearchRecord.find(SearchRecord.keywords == word1)
    for word in words[1:]:
        query = query.find(SearchRecord.keywords == word)

    query = query.sort('-episode_date')

    episode_results: list[Tuple[str, int]] = []
    record: SearchRecord
    async for record in query:
        episode_results.append((record.podcast_id, record.episode_number))

    trimmed_results = episode_results[:100]
    podcast_ids = {r[0] for r in trimmed_results}
    podcasts = await podcast_service.podcasts_for_ids(list(podcast_ids))

    all_episodes = []
    for podcast in podcasts:
        episode_numbers = [r[1] for r in trimmed_results if r[0] == podcast.id]

        episodes = await podcast_service.episodes_for_podcast_by_numbers_light(podcast, episode_numbers)
        all_episodes.extend(episodes)

    all_episodes.sort(key=lambda e: e.published_date, reverse=True)
    return RawSearchResult(episodes=all_episodes, podcasts=podcasts)


def build_keywords(search_text: str) -> set[str]:
    searchable_words = set()
    doc = nlp(search_text.lower())
    for word in doc:
        if word.lemma_ not in common_stop and word.lemma_.strip():
            searchable_words.add(word.lemma_.lower().strip())

    return searchable_words


async def search_search_index_task():
    await asyncio.sleep(indexing_startup)

    if not load_search_model():
        print(">>> Search Engine: Shutting down...")
        return

    while True:
        # noinspection PyBroadException
        try:
            await build_index_core()
        except Exception as x:
            print(f'!!! ERROR building search index: {x}')
        finally:
            await asyncio.sleep(indexing_frequency)


async def build_index_core():
    t0 = datetime.datetime.now()
    print('>>> Search Engine: Indexing starting... ')

    podcasts = await podcast_service.all_podcast()
    for podcast in podcasts:
        print(f'    >>> Search Engine: Indexing {podcast.title} ...', flush=True)
        await build_index_for_podcast(podcast)

    dt = datetime.datetime.now() - t0
    print(f'<<< Search Engine: Indexing complete in {dt.total_seconds():,.0f} seconds.', flush=True)


async def build_index_for_podcast(podcast: Podcast):
    html_converter = html2text.HTML2Text(bodywidth=10_000)
    html_converter.ignore_links = True

    base_text = (
            html_converter.handle(podcast.title or '')
            + ' '
            + html_converter.handle(podcast.description or '')
            + ' '
            + (podcast.website_url or '')
            + ' '
            + html_converter.handle(podcast.subtitle or '')
            + ' '
            + (podcast.category or '')
    )

    records = await search_records_lite_for_podcast(podcast.id)
    episode_to_record_date: dict[int: datetime.datetime] = {r.episode_number: r.created_date for r in records}

    for ep in await podcast_service.episodes_for_podcast(podcast):
        if not await has_changed_contents(episode_to_record_date, ep.podcast_id, ep.episode_number):
            # print(f'>>> Search Engine: NO CHANGES for episode {ep.episode_number} {ep.title}')
            continue

        print(f'        >>> Search Engine: Indexing episode {ep.title}')

        desc = html_converter.handle(ep.description or '')
        episode_text = (ep.title or '') + ' ' + desc + ' ' + ' '.join(ep.tags) + ' '
        episode_text += ' ' + base_text + ' '

        transcript: Optional[EpisodeTranscript] = await ai_service.full_transcript_for_episode(
            podcast.id,
            ep.episode_number)

        if transcript:
            transcript_text = ' '.join(w.text for w in transcript.words)
            episode_text += (
                    ' ' + (transcript.summary_bullets or '') + ' ' +
                    (transcript.summary_tldr or '') + ' ' + transcript_text
            )

        keywords: set[str] = build_keywords(episode_text.lower())

        record: Optional[SearchRecord] = await search_record_for_episode(podcast.id, ep.episode_number)

        if record is None:
            record = SearchRecord(
                podcast_id=podcast.id, episode_number=ep.episode_number, episode_id=ep.id, keywords=set()
            )

        record.keywords = keywords
        record.created_date = max(datetime.datetime.now(), ep.published_date)
        record.episode_date = ep.published_date

        await record.save()


async def has_changed_contents(
        episode_to_record_date: dict[int: datetime.datetime], podcast_id: str, episode_number: int
):
    search_date = episode_to_record_date.get(episode_number)
    if not search_date:
        # print('Returning TRUE, there are changes')
        return True

    changed_date = datetime.datetime(year=1900, month=1, day=1)

    episode = await podcast_service.episode_lite_by_number(podcast_id, episode_number)

    if episode and episode.published_date > changed_date:
        changed_date = episode.published_date

    transcript = await ai_service.transcript_lite_for_episode(podcast_id, episode_number)
    if transcript and transcript.updated_date > changed_date:
        changed_date = transcript.updated_date

    return changed_date >= search_date


async def search_record_for_episode(podcast_id: str, episode_number: int) -> Optional[SearchRecord]:
    record = await SearchRecord.find(
        SearchRecord.podcast_id == podcast_id, SearchRecord.episode_number == episode_number
    ).first_or_none()
    return record


async def search_records_lite_for_podcast(podcast_id: str) -> list[SearchRecord]:
    record = await SearchRecord.find(SearchRecord.podcast_id == podcast_id).project(SearchRecordLite).to_list()
    return record


async def latest_search_record_for_podcast(podcast_id: str) -> Optional[SearchRecord]:
    record = await (
        SearchRecord.find(SearchRecord.podcast_id == podcast_id)
        .project(SearchRecordLite)
        .sort('-created_date')
        .first_or_none()
    )
    return record


def load_search_model() -> bool:
    global nlp
    # noinspection PyBroadException
    try:
        nlp = spacy.load('en_core_web_lg')
        return True
    except Exception:
        print('WARNING: Search disabled. You must download the spacy model once to use search.')
        print('Run: python -m spacy download en_core_web_lg in the virtual env for this project.')
        return False


common_stop = {
    'i',
    'he',
    'she',
    'it',
    'the',
    'them',
    'as',
    'is',
    'um',
    'ah',
    'uh',
    'like',
    'also',
    'an',
    'and',
    'the',
    'to',
    'too',
    'if',
    'was',
    'or',
    # Include punctuation as that shouldn't be passed either
    '?',
    '.',
    ',',
    ':',
    ';',
    '!',
    '`',
    '/',
    '=',
    '-',
    '*',
    '**',
    '_',
    '__',
    "'",
    '--',
    ']',
    '[',
}
