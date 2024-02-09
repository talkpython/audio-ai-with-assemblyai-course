from pathlib import Path

import assemblyai
import chameleon_partials
import fastapi
import fastapi_chameleon
import uvicorn
from starlette.staticfiles import StaticFiles

from db import mongo_setup
from infrastructure import cache_buster, app_setup, app_secrets
from viewmodels.shared.viewmodel_base import ViewModelBase
from views import account_views, ai_views
from views import home_views
from views import podcasts_views
from views import search_views

hot_reload = False

development_mode = True
mongo_setup.development_mode = development_mode
app_setup.development_mode = development_mode

app = fastapi.FastAPI(docs_url=None,
                      redoc_url=None,
                      debug=development_mode,
                      lifespan=app_setup.app_lifespan
                      )


# #######################################################################
# Run with MongoDB in Docker as the database
#
# 1. Install Docker Desktop (or OrbStack)
#     https://www.docker.com/products/docker-desktop/
#     https://orbstack.dev
#
# 2. Pull the latest MongoDB Image:
#
#       docker pull mongo
#
# 3. Create a volume (local persistent storage) so the DB data persists across runs
#
#       docker volume create mongodata
#
# 4. Run the MongoDB server's container before starting the web app:
#
#       docker run -d --rm -p 127.0.0.1:27017:27017 -v mongodata:/data/db --name mongosvr mongo
#


def main():
    configure_secrets()
    configure_routing()
    configure_templating()
    configure_cache()


def configure_routing():
    app.mount('/static', StaticFiles(directory='static'), name='static')
    app.include_router(home_views.router)
    app.include_router(account_views.router)
    app.include_router(podcasts_views.router)
    app.include_router(ai_views.router)
    app.include_router(search_views.router)


def configure_templating():
    folder = (Path(__file__).parent / 'templates').as_posix()
    chameleon_partials.register_extensions(folder, auto_reload=development_mode)
    fastapi_chameleon.global_init(folder, auto_reload=development_mode)

    # Set dev mode for templates:
    ViewModelBase.dev_mode = development_mode and hot_reload


def configure_cache():
    # Set up cache busting for static content.
    folder = Path(__file__).parent.as_posix()
    cache_buster.global_init(development_mode, folder)


def configure_secrets():
    assemblyai.settings.api_key = app_secrets.assembly_ai_key


if __name__ == '__main__':
    main()
    uvicorn.run(app)
else:
    main()
