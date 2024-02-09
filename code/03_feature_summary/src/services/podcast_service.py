from typing import Optional

import bson
import httpx
from beanie.odm.operators.find.comparison import In

from db.episode import Episode, EpisodeLightProjection
from db.podcast import Podcast
from db.podcast_image import PodcastImage
from infrastructure import webutils
from services import user_service


async def podcast_from_title(title: str) -> Optional[Podcast]:
    podcast_id = webutils.to_url_style(title)
    if not podcast_id:
        return None

    return await Podcast.find_one(Podcast.id == podcast_id)


async def podcast_from_url(url_or_rss_url: str) -> Optional[Podcast]:
    if not url_or_rss_url:
        return None

    url_or_rss_url = url_or_rss_url.strip()

    podcast = await Podcast.find_one(Podcast.website_url == url_or_rss_url)
    if podcast:
        return podcast

    podcast = await Podcast.find_one(Podcast.rss_url == url_or_rss_url)
    return podcast


async def all_podcast(limit: int = 10_000) -> list[Podcast]:
    podcasts = await Podcast.find().sort('-last_updated').limit(limit).to_list()
    return podcasts


async def episodes_for_podcast(podcast: Podcast, limit_data=False) -> list[Episode]:
    if not limit_data:
        return await Episode.find(Episode.podcast_id == podcast.id).sort('-episode_number').to_list()
    else:
        return await (
            Episode.find(Episode.podcast_id == podcast.id)
            .sort('-episode_number')
            .project(EpisodeLightProjection)
            .to_list()
        )


async def episodes_for_podcast_light(podcast: Podcast) -> list[EpisodeLightProjection]:
    return (
        await Episode.find(Episode.podcast_id == podcast.id)
        .project(EpisodeLightProjection)
        .sort('-episode_number')
        .to_list()
    )


async def latest_episode_for_podcast(podcast_id: str) -> Optional[Episode]:
    return await Episode.find(Episode.podcast_id == podcast_id).sort('-episode_number').limit(1).first_or_none()


async def episodes_for_podcast_by_ids_light(
        podcast: Podcast, episode_ids: list[bson.ObjectId]
) -> list[EpisodeLightProjection]:
    return (
        await Episode.find(Episode.podcast_id == podcast.id, In(Episode.id, episode_ids))
        .project(EpisodeLightProjection)
        .sort('-episode_number')
        .to_list()
    )


async def episodes_for_podcast_by_numbers_light(
        podcast: Podcast, episode_numbers: list[int]
) -> list[EpisodeLightProjection]:
    return (
        await Episode.find(Episode.podcast_id == podcast.id, In(Episode.episode_number, episode_numbers))
        .project(EpisodeLightProjection)
        .sort('-episode_number')
        .to_list()
    )


async def follow_podcast(podcast_id: str, user_id: bson.ObjectId):
    user = await user_service.find_user_by_id(user_id)
    if not user:
        raise Exception(f'No user with ID {user_id}.')

    podcast = await Podcast.find_one(Podcast.id == podcast_id)
    if not podcast:
        raise Exception(f'No podcast with ID {podcast_id}.')

    user = await user_service.find_user_by_id(user_id)
    user.podcasts.extend(podcast.id)
    await user.save()


async def podcast_by_id(podcast_id: str) -> Optional[Podcast]:
    podcast = await Podcast.find_one(Podcast.id == podcast_id)
    return podcast


async def podcasts_for_ids(podcast_ids: list[str]) -> list[Podcast]:
    podcasts = await Podcast.find(In(Podcast.id, podcast_ids)).sort('-last_updated').to_list()
    return podcasts


async def delete_podcast(podcast: Podcast):
    await Episode.find(Episode.podcast_id == podcast.id).delete()
    await podcast.delete()


async def episode_by_number(podcast_id: str, episode_number: int) -> Optional[Episode]:
    episode = await Episode.find_one(Episode.podcast_id == podcast_id, Episode.episode_number == episode_number)
    return episode


async def episode_lite_by_number(podcast_id: str, episode_number: int) -> Optional[Episode]:
    episode = await (
        Episode.find(Episode.podcast_id == podcast_id, Episode.episode_number == episode_number)
        .project(EpisodeLightProjection)
        .first_or_none()
    )
    return episode


async def image_for_podcast(podcast_id: str) -> Optional[bytes]:
    image = await PodcastImage.find_one(PodcastImage.podcast_id == podcast_id)
    if not image:
        return None

    return image.content


async def save_image_for_podcast(podcast_id: str) -> Optional[bytes]:
    image_bytes = await image_for_podcast(podcast_id)
    if image_bytes:
        # Alternatively, delete and refresh it
        print(f'Skipping save image for podcast {podcast_id}, it already exists.')
        return image_bytes

    podcast: Podcast = await podcast_by_id(podcast_id)
    if not podcast:
        raise Exception(f'Podcast for {podcast_id} not found.')

    if not podcast.image:
        raise Exception(f'The podcast {podcast.title} has no image.')

    async with httpx.AsyncClient() as client:
        resp = await client.get(podcast.image, follow_redirects=True)
        resp.raise_for_status()

    image = PodcastImage(podcast_id=podcast_id, image_url=podcast.image, content=resp.content)
    await image.save()

    return image.content
