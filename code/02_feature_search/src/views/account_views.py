import asyncio

import fastapi
import fastapi_chameleon
from starlette import status
from starlette.requests import Request

from infrastructure import cookie_auth
from services import user_service
from viewmodels.account.register_viewmodel import RegisterViewModel
from viewmodels.account.signin_viewmodel import SigninViewModel
from viewmodels.shared.viewmodel_base import ViewModelBase

router = fastapi.APIRouter()


@router.get('/account/register')
@fastapi_chameleon.template('account/register.html')
def register_get(request: Request):
    if cookie_auth.get_user_id_via_auth_cookie(request):
        return fastapi.responses.RedirectResponse(url='/?from=register', status_code=status.HTTP_302_FOUND)

    return RegisterViewModel(request).to_dict()


@router.post('/account/register')
@fastapi_chameleon.template('account/register.html')
async def register_post(request: Request):
    model = RegisterViewModel(request)
    if not await model.load():
        return model.to_dict()

    user = await user_service.find_account_by_email(model.email)
    if user is not None:
        await asyncio.sleep(5)
        model.error = (
            f'An account with email {model.email} already exists. Did you mean to sign in instead? '
            f'Use the link below to sign in.'
        )
        return model.to_dict()

    user = await user_service.create_account(model.name, model.email, model.password)

    response = fastapi.responses.RedirectResponse(url='/?from=register', status_code=status.HTTP_302_FOUND)
    cookie_auth.login(response, user)

    return response


@router.get('/account/sign-in')
@fastapi_chameleon.template('account/sign-in.html')
def signin_get(request: Request):
    if cookie_auth.get_user_id_via_auth_cookie(request):
        return fastapi.responses.RedirectResponse(url='/?from=signin', status_code=status.HTTP_302_FOUND)

    return SigninViewModel(request).to_dict()


@router.post('/account/sign-in')
@fastapi_chameleon.template('account/sign-in.html')
async def signin_post(request: Request):
    if cookie_auth.get_user_id_via_auth_cookie(request):
        return fastapi.responses.RedirectResponse(url='/?from=signin', status_code=status.HTTP_302_FOUND)

    model = SigninViewModel(request)
    if not await model.load():
        return model.to_dict()

    user = await user_service.authenticate_user(model.email, model.password)
    if user is None:
        model.error = 'Invalid account password or email.'
        return model.to_dict()

    # Login user
    response = fastapi.responses.RedirectResponse(url='/?from=signin', status_code=status.HTTP_302_FOUND)
    cookie_auth.login(response, user)

    return response


@router.get('/account/forgot-password')
@fastapi_chameleon.template('account/forgot-password.html')
def forgot_get(request: Request):
    return ViewModelBase(request).to_dict()


@router.get('/account/reset-password')
@fastapi_chameleon.template('account/reset-password.html')
def reset_get(request: Request):
    return ViewModelBase(request).to_dict()


@router.post('/account/reset-password')
@fastapi_chameleon.template('account/reset-password.html')
def reset_post(request: Request):
    return ViewModelBase(request).to_dict()


@router.get('/account/logout')
def logout():
    response = fastapi.responses.RedirectResponse(url='/?from=logout', status_code=status.HTTP_302_FOUND)
    cookie_auth.logout(response)

    return response
