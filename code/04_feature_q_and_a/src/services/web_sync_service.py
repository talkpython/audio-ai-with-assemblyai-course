import asyncio
import datetime
from typing import Optional
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import httpx
import parsel

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
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    podcast = await podcast_service.podcast_from_url(url)
    if podcast:
        print(f'Found podcast from DB: {podcast.title}')
        return podcast

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, follow_redirects=True)

    if resp.status_code != 200:
        print(f'WARNING: What about this status code? {resp.status_code}')
        return None

    content_type: str = resp.headers.get('content-type', '').strip().lower()
    if content_type.startswith('text/html'):
        rss_url = search_page_for_rss_link(url, resp.text)
        print(f'found rss_url = {rss_url}')
        return await podcast_from_url(rss_url)

    podcast_rss: Element = ElementTree.fromstring(resp.text)
    channel = podcast_rss.find('channel')

    if not channel:
        print('Looks like this is an XML feed but not one for RSS.')
        return None

    title = channel.find('title').text.strip()

    podcast = await podcast_service.podcast_from_title(title)
    if podcast:
        return podcast

    podcast = await new_podcast_from_rss(channel, url, resp.headers.get('etag'))
    if podcast is None:
        return None

    await add_episodes_for_new_podcast(podcast, channel)

    return podcast


async def new_podcast_from_rss(channel: Element, url: str, etag: Optional[str]) -> Optional[Podcast]:
    title: str = channel.find('title').text.strip()
    if not title:
        return None

    channel.find('description')
    channel.get('itunes:summary')

    desc_node = or_element(channel.find('description'), channel.get('itunes:summary'))
    desc = (desc_node.text.strip() if desc_node is not None else '').strip() or None

    # noinspection HttpUrlsUsage
    itunes_ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}

    subtitle_node = or_element(channel.find('subtitle'), channel.find('itunes:subtitle', itunes_ns))
    subtitle = None
    if subtitle_node is not None:
        subtitle = (subtitle_node.text.strip() if subtitle_node.text else '').strip() or None

    category_node = or_element(channel.find('category'), channel.find('itunes:category', itunes_ns))
    category = None
    if category_node is not None:
        category = category_node.attrib.get('text', '').strip() or None

    image_node = or_element(channel.find('itunes:image', itunes_ns), channel.find('image'))
    image = None
    if image_node is not None:
        image = image_node.attrib.get('href')
    if image_node is not None and not image:
        url_node = image_node.find('url')
        if url_node is not None:
            image = url_node.text
    if image:
        image = image.strip()

    website_url_node = channel.find('link')
    website_url = None
    if website_url_node is not None:
        website_url = (
                          website_url_node.text.strip().rstrip('/') if website_url_node is not None else ''
                      ).strip() or None

    items = channel.findall('item')
    if not items:
        return None

    podcast = Podcast(
        id=webutils.to_url_style(title),
        title=title.strip(),
        description=desc,
        subtitle=subtitle,
        category=category,
        image=image,
        website_url=website_url,
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


async def add_episodes_for_new_podcast(podcast: Podcast, channel: Element):
    db_episodes = await podcast_service.episodes_for_podcast_light(podcast)
    existing_ids = {e.episode_number for e in db_episodes}
    existing_ids.update({e.episode_number for e in db_episodes})

    # noinspection HttpUrlsUsage
    itunes_ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}

    items = channel.findall('item')

    episodes_to_add = []
    for idx, e in enumerate(items):
        title = e.find('title').text.strip()
        episode_guid = e.find('guid').text.strip() or None
        number_node = e.find('itunes:episode', itunes_ns)
        if number_node is None:
            print(f'No episode number for {title}, skipping...')
            continue

        episode_number = int(number_node.text)
        if episode_guid in existing_ids or episode_number in existing_ids:
            continue

        # <pubDate>Sun, 15 Oct 2023 00:00:00 -0800</pubDate>
        date_str = e.find('pubDate').text
        try:
            pub_date = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        except ValueError:
            pub_date = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        link_node = e.find('link')
        episode_url = None
        if link_node is not None:
            episode_url = link_node.text.strip()

        duration_text = e.find('itunes:duration', itunes_ns).text.strip() or None

        summary_node = e.find('itunes:summary', itunes_ns)
        summary = summary_node.text.strip() if summary_node else None
        description_node = or_element(e.find('description'), e.find('content'))
        description = description_node.text.strip()

        if summary == description:
            summary = None
            print('No summary stored, same as description.')
        enclosure_url = None
        enclosure_type = None
        enclosure_length_bytes = 0
        link = e.find('enclosure')
        if link is not None and 'audio' in link.attrib.get('type', ''):
            enclosure_type = link.attrib.get('type', '')
            enclosure_url = link.attrib.get('url', '').strip() or None
            enclosure_length_bytes = int(link.attrib.get('length', '0'))

        tags = []

        # noinspection PyBroadException
        try:
            tags = [t.strip().lower() for t in e.find('itunes:keywords', itunes_ns).text.split(',')]
        except Exception:
            pass  # Yes, we will try/except/pass!

        explicit = str(e.find('itunes:explicit', itunes_ns) or 'no').lower().strip() in {'yes', 'true'}

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

    if episodes_to_add:
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


def or_element(primary: Optional[Element], fallback: Optional[Element]) -> Optional[Element]:
    # Why does this need to exist? For some reason bool(non_empty_element) is False?
    if primary is not None:
        return primary
    elif fallback is not None:
        return fallback

    return None


async def load_starter_data():
    podcast_urls = [
        'https://talkpython.fm/rss',
        'https://pythonbytes.fm/rss',
        'https://feeds.megaphone.fm/darknetdiaries',
        'https://feeds.megaphone.fm/STU4418364045',
        'https://feeds.megaphone.fm/replyall',
        'https://atp.fm/episodes?format=rss',
        # '',
    ]

    for url in podcast_urls:
        # noinspection PyAsyncCall
        asyncio.create_task(podcast_from_url(url))
