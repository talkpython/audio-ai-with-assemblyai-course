import hashlib
from datetime import timedelta
from typing import Optional, Final

import bson
from starlette.requests import Request
from starlette.responses import Response

from db.user import User

AUTH_COOKIE_NAME: Final[str] = 'user_xray_podcasts'

dev_mode = True


def get_user_id_via_auth_cookie(request: Request) -> Optional[bson.ObjectId]:
    cookie_value = request.cookies.get(AUTH_COOKIE_NAME)
    if not cookie_value:
        return None

    # noinspection PyBroadException
    try:
        parts = cookie_value.split(':')
        if len(parts) not in {2, 3}:
            return None

        user_id = parts[0]
        hash_txt = parts[1]
    except Exception as x:
        print(f'Error parsing auth cookie value: val: {cookie_value}, error: {x}')
        return None

    expected_hash = hashlib.sha256(f'salty_{user_id}_id'.encode('utf-8')).hexdigest()
    if expected_hash != hash_txt:
        print(f'Bad hash in cookie: cookie_value={cookie_value}')
        return None

    try:
        return bson.ObjectId(user_id)
    except bson.errors.InvalidId:
        return None


def login(response: Response, user: User):
    val = __get_cookie_value(user)
    sec = not dev_mode
    age = int(timedelta(days=90).total_seconds())
    response.set_cookie(key=AUTH_COOKIE_NAME, value=val, max_age=age, secure=sec, httponly=True, samesite='lax')


def __get_cookie_value(user):
    password_marker = __compute_password_expiry_key_for_user(user)

    hash_txt = hashlib.sha256(('salty_' + str(user.id) + '_id').encode('utf-8')).hexdigest()
    val = f'{user.id}:{hash_txt}:{password_marker}'
    return val


def __compute_password_expiry_key_for_user(user):
    h = hashlib.md5(user.password_hash.encode())
    hv = h.hexdigest()
    password_marker = hv[1:8]

    return password_marker


def logout(response: Response):
    response.delete_cookie(key=AUTH_COOKIE_NAME)
