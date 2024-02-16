from typing import Any, Optional, Callable

import bson
import chameleon_partials
from starlette.requests import Request

from db.user import User
from infrastructure import cache_buster, cookie_auth
from services import user_service


class ViewModelBase:
    dev_mode = False

    def __init__(self, request: Request, error: Optional[str] = None):
        self.error = error
        self.request = request
        self.render_partial: Callable = chameleon_partials.render_partial
        self.cache_id = cache_buster.cache_id
        self.user_id: Optional[bson.ObjectId] = cookie_auth.get_user_id_via_auth_cookie(request)
        self.user: Optional[User] = None
        self.viewmodel = self

    def to_dict(self) -> dict[str, Any]:
        data = self.__dict__.copy()
        data['dev_mode'] = self.dev_mode

        return data

    async def load(self) -> bool:
        raise Exception(f'Model specific form load and validation not set on class {type(self).__name__}.')

    async def load_user(self):
        if self.user_id:
            self.user = await user_service.logged_in_user(self.request)

        if not self.user:
            self.user_id = None
