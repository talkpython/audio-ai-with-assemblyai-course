import fastapi
import fastapi_chameleon
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from db.podcast import Podcast
from infrastructure import webutils
from services import web_sync_service, podcast_service, user_service, search_service, ai_service
from viewmodels.podcasts.episode_chat_viewmodel import EpisodeChatViewModel
from viewmodels.podcasts.follow_podcast_viewmodel import FollowPodcastViewModel
from viewmodels.podcasts.podcasts_details_viewmodel import PodcastDetailsViewModel
from viewmodels.podcasts.podcasts_episode_viewmodel import PodcastEpisodeViewModel
from viewmodels.podcasts.podcasts_followed_viewmodel import PodcastFollowedViewModel
from viewmodels.podcasts.podcasts_index_viewmodel import PodcastIndexViewModel

router = fastapi.APIRouter()


@router.get('/podcasts')
@fastapi_chameleon.template('podcasts/index.html')
async def index_get(request: Request):
    vm = PodcastIndexViewModel(request)
    await vm.load_data()
    return vm.to_dict()


@router.get('/podcasts/followed')
@fastapi_chameleon.template('podcasts/followed.html')
async def followed(request: Request):
    vm = PodcastFollowedViewModel(request)
    await vm.load_data()

    if not vm.user or not vm.user_podcasts:
        return webutils.redirect_to('/podcasts')

    return vm.to_dict()


@router.post('/podcasts')
@fastapi_chameleon.template('podcasts/index.html')
async def index_post(request: Request):
    vm = FollowPodcastViewModel(request)
    if not await vm.load():
        return vm.to_dict()

    try:
        print(f'Looking for podcast {vm.podcast_url} ...')
        podcast = await web_sync_service.podcast_from_url(vm.podcast_url)
        if podcast is None:
            vm.error = f"We could not locate a podcast at the url '{vm.podcast_url}'."
            return vm.to_dict()

        print(f'Created {podcast}')
        if vm.user:
            await podcast_service.follow_podcast(podcast.id, vm.user_id)
        search_service.manually_trigger_index_build()

        return webutils.redirect_to(f'/podcasts/details/{podcast.id}')
    except Exception as x:
        vm.error = f'Error parsing {vm.podcast_url}: {x}'
        return vm.to_dict()


@router.get('/podcasts/hx-follow/{podcast_id}')
async def index(request: Request, podcast_id: str):
    if not podcast_id:
        error = 'You must specify a podcast url.'
        return webutils.return_error(error, status_code=status.HTTP_400_BAD_REQUEST)

    try:
        podcast = await podcast_service.podcast_from_title(podcast_id)
        if not podcast:
            error = f'Podcast does not exist for {podcast_id}'
            return webutils.return_error(error, status.HTTP_404_NOT_FOUND)

        user = await user_service.logged_in_user(request)
        if user is None:
            error = 'User not logged in.'
            print(error)
            return webutils.return_error(error, status.HTTP_400_BAD_REQUEST)

        await podcast_service.follow_podcast(podcast.id, user.id)
        print(f'Following {podcast.title} for {user.name}.')

        return webutils.html_response('podcasts/partials/followed_podcast_button.html')
    except Exception as x:
        error = f'Error parsing {podcast_id}: {x}'
        print(error)
        return webutils.return_error(error, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get('/podcasts/details/{podcast_id}')
@fastapi_chameleon.template('podcasts/details.html')
async def details(request: Request, podcast_id: str):
    vm = PodcastDetailsViewModel(request, podcast_id)
    await vm.load_data()
    if vm.podcast is None:
        return fastapi_chameleon.engine.response('errors/404.html', status_code=404)

    return vm.to_dict()


@router.get('/podcasts/details/{podcast_id}/episode/{episode_number}')
@fastapi_chameleon.template('podcasts/episode.html')
async def episode(request: Request, podcast_id: str, episode_number: int):
    vm = PodcastEpisodeViewModel(request, podcast_id, episode_number)
    await vm.load_data()
    if vm.episode is None:
        return fastapi_chameleon.engine.response('errors/404.html', status_code=404)

    return vm.to_dict()


@router.get('/podcasts/image/{podcast_id}.{ext}')
async def image(podcast_id: str, ext: str):
    img_bytes = await podcast_service.image_for_podcast(podcast_id)
    if not img_bytes:
        img_bytes = await podcast_service.save_image_for_podcast(podcast_id)

    if not img_bytes:
        return webutils.return_error(f'No image found for podcast {podcast_id}', status_code=404)

    img_type = 'jpeg' if ext == 'jpg' else ext

    seconds_per_day = 60 * 60 * 24
    response = Response(content=img_bytes, media_type=f'image/{img_type}', status_code=200)
    response.headers['Cache-Control'] = f'max-age={365 * seconds_per_day}'

    return response


@router.get('/podcasts/transcript/{podcast_id}/episode/{episode_number}')
@fastapi_chameleon.template('podcasts/transcript.html')
async def transcript(request: Request, podcast_id: str, episode_number: int):
    vm = PodcastEpisodeViewModel(request, podcast_id, episode_number)
    await vm.load_data()
    return vm.to_dict()


@router.get('/podcasts/hx-episodes/{podcast_id}')
@fastapi_chameleon.template('podcasts/partials/episodes-in-podcast.html')
async def episodes_in_podcast(request: Request, podcast_id: str):
    vm = PodcastDetailsViewModel(request, podcast_id)
    await vm.load_data()
    return vm.to_dict()


@router.get('/podcasts/chat/{podcast_id}/episode/{episode_number}')
@fastapi_chameleon.template('podcasts/chat-with-episode.html')
async def chat_with_episode(request: Request, podcast_id: str, episode_number: int):
    vm = EpisodeChatViewModel(request, podcast_id, episode_number)
    await vm.load_data()
    return vm.to_dict()


@router.post('/podcasts/hx-question/{podcast_id}/episode/{episode_number}')
@fastapi_chameleon.template('podcasts/partials/chat-response.html')
async def chat_response(request: Request, podcast_id: str, episode_number: int):
    vm = EpisodeChatViewModel(request, podcast_id, episode_number)
    await vm.load_data()

    if vm.error:
        return vm.to_dict()

    chat = await ai_service.ask_chat(podcast_id, episode_number, vm.user.email, vm.question)
    vm.set_answer(chat.answer)
    return vm.to_dict()


@router.get('/podcasts/refresh-podcast/{podcast_id}')
async def refresh_podcast(podcast_id: str):
    podcast = await podcast_service.podcast_by_id(podcast_id)
    if podcast is None:
        return fastapi.responses.HTMLResponse(content='No podcast with that ID', status_code=404)

    rss_url = podcast.rss_url
    await podcast_service.delete_podcast(podcast)

    podcast: Podcast = await web_sync_service.podcast_from_url(rss_url)
    return webutils.redirect_to(f'/podcasts/details/{podcast.id}')
