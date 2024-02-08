import datetime
from pathlib import Path
from typing import Optional

import beanie
import pydantic
import pymongo


class Podcast(beanie.Document):
    id: str
    title: str
    created_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    last_updated: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)

    description: Optional[str] = None
    subtitle: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None
    itunes_type: Optional[str] = None
    website_url: Optional[str] = None
    rss_url: str
    latest_rss_etag: Optional[str] = None
    latest_rss_modified: Optional[str] = None

    class Settings:
        name = 'podcasts'
        indexes = [
            pymongo.IndexModel(keys=[('created_date', pymongo.ASCENDING)], name='created_date_ascend'),
            pymongo.IndexModel(keys=[('last_updated', pymongo.DESCENDING)], name='last_updated_descending'),
            pymongo.IndexModel(keys=[('category', pymongo.ASCENDING)], name='category_ascend'),
            pymongo.IndexModel(keys=[('itunes_type', pymongo.ASCENDING)], name='itunes_type_ascend'),
            pymongo.IndexModel(keys=[('website_url', pymongo.ASCENDING)], name='website_url_ascend'),
            pymongo.IndexModel(keys=[('rss_url', pymongo.ASCENDING)], name='rss_url_ascend'),
        ]

    @property
    def cached_image_url(self) -> Optional[str]:
        if not self.image:
            return None

        ext = Path(self.image).suffix.strip('.') or 'png'
        url = f'/podcasts/image/{self.id}.{ext}'

        return url
