import asyncio
from typing import Optional

import bson
from passlib.hash import argon2
from starlette.requests import Request

from db.user import User
from infrastructure import cookie_auth


async def create_account(name: Optional[str], email: str, password: str, is_admin=False) -> User:
    print(f'Creating new account for {name} @ {email}')

    if not email or not email.strip() or not password or not password.strip():
        raise ValueError('Data is missing to created an account.')

    email = email.strip().lower()
    name = (name or '').strip()

    user = User(
        name=name,
        email=email,
        password_hash=argon2.hash(password),
        is_admin=is_admin,
    )

    await user.save()

    print(f'New account created for {email}')
    return await find_account_by_email(email)


async def find_account_by_email(email: str) -> Optional[User]:
    if not email or not email.strip():
        return None

    email = email.strip().lower()
    return await User.find_one(User.email == email)


async def authenticate_user(email: str, plain_text_password: str) -> Optional[User]:
    user = await find_account_by_email(email)
    if user is None:
        await asyncio.sleep(3)
        return None

    if not verify_password(plain_text_password, user.password_hash):
        await asyncio.sleep(3)
        return None

    return user


def verify_password(plain_text_password: str, password_hash: str) -> bool:
    if not plain_text_password:
        return False

    return argon2.verify(plain_text_password, password_hash)


async def find_user_by_id(user_id: bson.ObjectId) -> Optional[User]:
    return await User.find_one(User.id == user_id)


async def logged_in_user(request: Request) -> Optional[User]:
    user_id = cookie_auth.get_user_id_via_auth_cookie(request)
    if not user_id:
        return None

    user = await find_user_by_id(user_id)
    return user
