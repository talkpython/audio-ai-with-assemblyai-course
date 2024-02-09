import fastapi
import fastapi_chameleon
from starlette.requests import Request

from viewmodels.shared.viewmodel_base import ViewModelBase

router = fastapi.APIRouter()


@router.get('/')
@fastapi_chameleon.template('home/index.html')
def index(request: Request):
    return ViewModelBase(request).to_dict()
