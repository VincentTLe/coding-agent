"""Bank service over the models in ``models.py`` (IMPLEMENT THIS FILE).

Every method below raises ``NotImplementedError``. Replace the bodies so the
service behaves exactly as the docstrings (and ``test_bank.py``) require. You
will need to READ ``models.py`` to use ``Account``, its ``can_debit`` /
``available`` helpers, the ``BankError`` hierarchy, and ``TransactionLog``.

Money is always an integer number of cents. Do not introduce floats.
"""

from __future__ import annotations

from models import (
    Account,
    AccountFrozen,
    AccountNotFound,
    InsufficientFunds,
    InvalidAmount,
    TransactionLog,
)


class Bank:
    """Holds accounts and a shared transaction log."""

    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.log = TransactionLog()

    def open_account(self, account_id: str, *, overdraft_limit: int = 0) -> Account:
        """Create and register a new account with zero balance.

        Raises ``ValueError`` if an account with this id already exists, or if
        ``overdraft_limit`` is negative. Returns the created ``Account``.
        """
        raise NotImplementedError

    def get(self, account_id: str) -> Account:
        """Return the account, or raise ``AccountNotFound`` if unknown."""
        raise NotImplementedError

    def deposit(self, account_id: str, amount: int) -> None:
        """Credit ``amount`` cents to the account.

        ``amount`` must be a positive ``int`` (``bool`` is NOT a valid int
        here) — otherwise raise ``InvalidAmount``. A frozen account may still
        receive deposits. On success the balance increases and a credit of
        ``+amount`` is recorded in the log.
        """
        raise NotImplementedError

    def withdraw(self, account_id: str, amount: int) -> None:
        """Debit ``amount`` cents from the account.

        ``amount`` must be a positive ``int`` (reject ``bool``) or raise
        ``InvalidAmount``. If the account is frozen raise ``AccountFrozen``.
        If the debit would exceed the account's available balance (balance +
        overdraft_limit) raise ``InsufficientFunds``. On success the balance
        decreases and a debit of ``-amount`` is recorded in the log.

        Checks happen in this order: amount validity, then frozen, then funds.
        """
        raise NotImplementedError

    def transfer(self, src_id: str, dst_id: str, amount: int) -> None:
        """Move ``amount`` cents from ``src_id`` to ``dst_id`` atomically.

        Both accounts must exist (else ``AccountNotFound``). ``src_id`` and
        ``dst_id`` must differ — raise ``ValueError`` if they are equal. The
        transfer must be ALL-OR-NOTHING: if the debit from the source cannot
        proceed (frozen / insufficient funds / invalid amount), neither
        balance changes and NOTHING is written to the log. On success the log
        contains exactly the source debit followed by the destination credit.
        """
        raise NotImplementedError

    def net_position(self) -> int:
        """Return the sum of all account balances, in cents."""
        raise NotImplementedError
