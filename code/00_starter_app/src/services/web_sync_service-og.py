import datetime
import time
from typing import Optional

import feedparser
import httpx
import parsel
from feedparser import FeedParserDict

from db.episode import Episode
from db.podcast import Podcast
from infrastructure import webutils, date_data
from services import podcast_service


async def podcast_from_url(url: str) -> Optional[Podcast]:
    # 1. Download the content
    #     - Is it HTML, look for RSS link, call recursion!
    #     - Is it RSS? Parse that.
    # 2. Take parsed content and look for the podcast name
    #     - Exists in DB? Return DB version.
    #     - No? Create and insert the podcast, return that.
    if not url or not url.strip():
        return None

    url = url.strip()

    podcast = await podcast_service.podcast_from_url(url)
    if podcast:
        print(f'Found podcast from DB: {podcast.title}')
        return podcast

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, follow_redirects=True)

    if resp.status_code != 200:
        print(f'WARNING: What about this status code? {resp.status_code}')
        return None

    content_type: str = resp.headers.get('content-type', '').strip()
    if content_type.startswith('text/html'):
        rss_url = search_page_for_rss_link(url, resp.text)
        print(f'found rss_url = {rss_url}')
        return await podcast_from_url(rss_url)

    podcast_rss: FeedParserDict = feedparser.parse(resp.text)
    if not podcast_rss.get('feed'):
        print('Looks like this is an XML feed but not one for RSS.')
        return None

    podcast_feed = podcast_rss['feed']
    title = podcast_feed['title']

    podcast = await podcast_service.podcast_from_title(title)
    if podcast:
        return podcast

    podcast = await new_podcast_from_rss(podcast_rss, url, resp.headers.get('etag'))
    if podcast is None:
        return None

    await add_episodes_for_new_podcast(podcast, podcast_rss)

    return podcast


async def new_podcast_from_rss(podcast_rss: FeedParserDict, url: str, etag: Optional[str]) -> Optional[Podcast]:
    feed = podcast_rss['feed']
    title: str = feed['title'] or ''
    if not title:
        return None

    podcast = Podcast(
        id=webutils.to_url_style(title),
        title=title.strip(),
        description=(feed.get('description') or feed.get('itunes:summary') or '').strip(),
        subtitle=(feed.get('subtitle') or feed.get('itunes:subtitle') or '').strip() or None,
        category=(feed.get('category') or '').strip() or None,
        image=(feed.get('image', {}).get('href') or '').strip() or None,
        itunes_type=(feed.get('itunes_type') or '').strip() or None,
        website_url=(feed.get('link') or '').strip().rstrip('/') or None,
        rss_url=url.strip().rstrip('/'),
        latest_rss_modified=__get_feed_date_text(datetime.datetime.now()),
        latest_rss_etag=etag,
    )

    await podcast.save()
    return podcast


def search_page_for_rss_link(base_url: str, html_text: str) -> Optional[str]:
    rss_url = None
    selector = parsel.Selector(text=html_text)
    for link in selector.css('head > link'):
        rel = link.xpath('.//@rel').get()
        rel_type = link.xpath('.//@type').get()
        href = link.xpath('.//@href').get()

        if rel == 'alternate' and rel_type == 'application/rss+xml' and href:
            rss_url = href.strip()
            break

    if rss_url and rss_url.strip().startswith('/'):
        rss_url = base_url.rstrip('/') + rss_url

    return rss_url


async def add_episodes_for_new_podcast(podcast: Podcast, podcast_rss: FeedParserDict):
    db_episodes = await podcast_service.episodes_for_podcast_light(podcast)
    existing_ids = {e.episode_guid for e in db_episodes}
    existing_ids.update({e.episode_number for e in db_episodes})

    episodes_to_add = []
    for e in podcast_rss.entries:
        episode_guid = e.get('id', '').strip() or None
        episode_number = int(e.get('itunes_episode', 0))
        if episode_guid in existing_ids or episode_number in existing_ids:
            continue

        title = e.get('title', '').strip()
        # <pubDate>Sun, 15 Oct 2023 00:00:00 -0800</pubDate>
        p: time.struct_time = e.published_parsed
        pub_date = datetime.datetime(
            year=p.tm_year, month=p.tm_mon, day=p.tm_mday, hour=p.tm_hour, minute=p.tm_min, second=p.tm_sec
        )
        episode_url = e.get('link', '').strip()
        duration_text = e.get('itunes_duration', '').strip() or None
        if episode_number == 359:
            d1 = e.get('description', '')
            d2 = e.get('summary_detail', {}).get('value', '').strip() or None

        description = e.get('description', '').strip() or e.get('summary_detail', {}).get('value', '').strip() or None
        if not description:
            content = e.get('content')
            if content and isinstance(content, list):
                description = content[0].get('value', '').strip() or None

        summary = e.get('summary', '').strip() or e.get('itunes_summary', '').strip() or None
        if summary == description:
            summary = None
            print('No summary stored, same as description.')
            # if len(description) > 200:
            #     md = html2text(description)
            #     summary = textwrap.shorten(md, width=450, placeholder='...')
        enclosure_url = None
        enclosure_type = None
        enclosure_length_bytes = 0
        for link in e.get('links'):
            if 'audio' in link.get('type', ''):
                enclosure_type = link.get('type')
                enclosure_url = link.get('href', '').strip() or None
                enclosure_length_bytes = int(link.get('length', ''))
                break

        tags = []

        # noinspection PyBroadException
        try:
            tags = [t['term'] for t in e.tags]
        except Exception:
            pass  # Yes, we will try/except/pass!

        explicit = str(e.get('itunes_explicit', 'no') or 'no').lower().strip() in {'yes', 'true'}

        duration_in_sec = __seconds_from_duration_text(duration_text)

        episode = Episode(
            title=title,
            published_date=pub_date,
            episode_guid=episode_guid,
            episode_number=episode_number,
            podcast_id=podcast.id,
            episode_url=episode_url,
            duration_text=duration_text,
            duration_in_sec=duration_in_sec,
            summary=summary,
            description=description,
            enclosure_url=enclosure_url,
            enclosure_type=enclosure_type,
            enclosure_length_bytes=enclosure_length_bytes,
            tags=tags,
            explicit=explicit,
        )

        episodes_to_add.append(episode)

    await Episode.insert_many(episodes_to_add)


def __get_feed_date_text(d):
    data = {
        'day': date_data.days[d.weekday()],
        'day_of_month': str(d.day).zfill(2),
        'month': date_data.months[d.month - 1],
        'year': d.year,
        'hour': str(d.hour).zfill(2),
        'minute': str(d.minute).zfill(2),
        'second': str(d.second).zfill(2),
    }
    return '{day}, {day_of_month} {month} {year} {hour}:{minute}:{second} -0800'.format(**data)
    # return d.strftime('%a, %d %b %Y %H:%M:%S')


def __seconds_from_duration_text(duration_text: str) -> int:
    # E.g. 01:03:40
    if not duration_text or not duration_text.strip():
        return 0

    parts = duration_text.split(':')
    if len(parts) < 2:
        return 0

    if len(parts) == 2:
        mins = int(parts[0])
        sec = int(parts[1])
        return mins * 60 + sec

    if len(parts) == 3:
        hrs = int(parts[0])
        mins = int(parts[1])
        sec = int(parts[2])
        return hrs * 60 * 60 + mins * 60 + sec

    return 0
