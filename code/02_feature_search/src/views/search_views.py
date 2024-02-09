
import fastapi
import fastapi_chameleon
from starlette.requests import Request

from viewmodels.search.search_results_viewmodel import SearchResultsViewModel

router = fastapi.APIRouter()


@router.get('/search')
@fastapi_chameleon.template('search/index.html')
def search_get(request: Request):
    return SearchResultsViewModel(request, '').to_dict()
