from typing import Optional

import fastapi
import fastapi_chameleon
from starlette.requests import Request

from services import search_service
from services.search_service import RawSearchResult
from viewmodels.search.search_results_viewmodel import SearchResultsViewModel

router = fastapi.APIRouter()


@router.get('/search')
@fastapi_chameleon.template('search/index.html')
def search_get(request: Request):
    return SearchResultsViewModel(request, '').to_dict()


@router.get('/search/hx-search')
@fastapi_chameleon.template('search/partials/search_results.html')
async def search_hx_results(request: Request, search_text: Optional[str] = None):
    vm = SearchResultsViewModel(request, search_text)
    await vm.load()

    return vm.to_dict()
