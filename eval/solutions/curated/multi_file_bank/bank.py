"""Reference solution for bank.py."""

from __future__ import annotations

from models import (
    Account,
    AccountFrozen,
    AccountNotFound,
    InsufficientFunds,
    InvalidAmount,
    TransactionLog,
)


def _validate_amount(amount) -> None:
    # bool is an int subclass; reject it explicitly as a money amount.
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise InvalidAmount(f"amount must be a positive int of cents, got {amount!r}")


class Bank:
    """Holds accounts and a shared transaction log."""

    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.log = TransactionLog()

    def open_account(self, account_id: str, *, overdraft_limit: int = 0) -> Account:
        if account_id in self.accounts:
            raise ValueError(f"account {account_id!r} already exists")
        if overdraft_limit < 0:
            raise ValueError("overdraft_limit must be non-negative")
        acct = Account(id=account_id, balance=0, overdraft_limit=overdraft_limit)
        self.accounts[account_id] = acct
        return acct

    def get(self, account_id: str) -> Account:
        try:
            return self.accounts[account_id]
        except KeyError:
            raise AccountNotFound(account_id)

    def deposit(self, account_id: str, amount: int) -> None:
        _validate_amount(amount)
        acct = self.get(account_id)
        acct.balance += amount
        self.log.record(account_id, amount)

    def withdraw(self, account_id: str, amount: int) -> None:
        _validate_amount(amount)
        acct = self.get(account_id)
        if acct.frozen:
            raise AccountFrozen(account_id)
        if not acct.can_debit(amount):
            raise InsufficientFunds(account_id)
        acct.balance -= amount
        self.log.record(account_id, -amount)

    def transfer(self, src_id: str, dst_id: str, amount: int) -> None:
        if src_id == dst_id:
            raise ValueError("cannot transfer to the same account")
        src = self.get(src_id)
        dst = self.get(dst_id)
        # Validate everything BEFORE mutating anything (all-or-nothing).
        _validate_amount(amount)
        if src.frozen:
            raise AccountFrozen(src_id)
        if not src.can_debit(amount):
            raise InsufficientFunds(src_id)
        src.balance -= amount
        dst.balance += amount
        self.log.record(src_id, -amount)
        self.log.record(dst_id, amount)

    def net_position(self) -> int:
        return sum(a.balance for a in self.accounts.values())
