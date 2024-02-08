from typing import Optional

from starlette.requests import Request

from viewmodels.shared.viewmodel_base import ViewModelBase


class SigninViewModel(ViewModelBase):
    def __init__(self, request: Request):
        super().__init__(request)
        self.password: Optional[str] = None
        self.email: Optional[str] = None

    async def load(self) -> bool:
        form = await self.request.form()
        self.password = (form.get('password') or '').strip()
        self.email = (form.get('email') or '').strip().lower()

        if not self.email:
            self.error = 'The email is required.'
            return False

        if not self.password:
            self.error = 'You must enter a password.'
            return False

        return not self.error
