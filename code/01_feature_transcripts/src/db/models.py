from db.chat import ChatQA
from db.episode import Episode
from db.job import BackgroundJob
from db.podcast import Podcast
from db.podcast_image import PodcastImage
from db.search_record import SearchRecord
from db.transcripts import EpisodeTranscript
from db.user import User

all_models = [
    ChatQA,
    Episode,
    Podcast,
    User,
    EpisodeTranscript,
    SearchRecord,
    BackgroundJob,
    PodcastImage,
]
