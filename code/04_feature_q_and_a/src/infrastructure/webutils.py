from typing import Optional

import fastapi_chameleon
from starlette import status
from starlette.responses import RedirectResponse, PlainTextResponse, Response


def to_url_style(text):
    if not text:
        return text

    text = text.strip()
    url_txt = ''.join(ch if ch.isalnum() or ch == '.' else ' ' for ch in text)

    count = -1
    while count != len(url_txt):
        count = len(url_txt)
        url_txt = url_txt.strip()
        url_txt = url_txt.replace('  ', ' ')
        url_txt = url_txt.replace(' ', '-')
        url_txt = url_txt.replace('--', '-')

    return url_txt.lower().strip()


def redirect_to(url: str, permanent: bool = False) -> Response:
    stat = status.HTTP_302_FOUND if not permanent else status.HTTP_301_MOVED_PERMANENTLY
    return RedirectResponse(url=url, status_code=stat)


def return_error(error_msg: str, status_code: int) -> Response:
    return PlainTextResponse(content=error_msg, status_code=status_code)


def return_not_found() -> Response:
    return PlainTextResponse(content='This resource was not found.', status_code=404)


def html_response(
        template_file: str, model: Optional[dict] = None, media_type: str = 'text/html', status_code: int = 200
) -> Response:
    if model is None:
        model = {}

    html = fastapi_chameleon.engine.render(template_file, **model)

    return Response(content=html, media_type=media_type, status_code=status_code)
