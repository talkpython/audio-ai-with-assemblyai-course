class AccountError(Exception):
    pass


class AccountNotFoundError(AccountError):
    def __init__(self, account_id):
        self.account_id = account_id

    def __str__(self):
        return f'Account with identifier {self.account_id} was not found'

    def __repr__(self):
        return str(self)


class InvalidPasswordError(AccountError):
    def __init__(self, account_id):
        self.account_id = account_id

    def __str__(self):
        return f'The provided password for account with identifier {self.account_id} was incorrect'

    def __repr__(self):
        return str(self)
