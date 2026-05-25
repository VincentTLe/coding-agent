"""Domain models for the bank service (COMPLETE — do not modify).

`bank.py` must be implemented against the behaviour defined here. Read this
file carefully: the rules about money units, overdraft, and frozen accounts
all live in these classes, and `bank.py` is expected to use them rather than
re-implement them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class BankError(Exception):
    """Base class for all bank-related errors."""


class AccountNotFound(BankError):
    """Raised when an account id is not registered with the bank."""


class InsufficientFunds(BankError):
    """Raised when a debit would exceed an account's available balance."""


class AccountFrozen(BankError):
    """Raised when a debit is attempted against a frozen account."""


class InvalidAmount(BankError):
    """Raised when an amount is not a positive whole number of cents."""


@dataclass
class Account:
    """A single bank account.

    Money is stored as an integer number of CENTS — never floats — so that
    arithmetic is exact. ``balance`` may be negative down to
    ``-overdraft_limit`` (also in cents).

    Attributes:
        id: unique account identifier.
        balance: current balance in cents (may be negative within overdraft).
        overdraft_limit: how far below zero the balance may go, in cents
            (a non-negative number). 0 means no overdraft allowed.
        frozen: when True the account may receive credits but rejects debits.
    """

    id: str
    balance: int = 0
    overdraft_limit: int = 0
    frozen: bool = False

    def available(self) -> int:
        """Cents that may currently be withdrawn = balance + overdraft_limit."""
        return self.balance + self.overdraft_limit

    def can_debit(self, amount: int) -> bool:
        """True iff ``amount`` cents can be debited right now.

        A debit is allowed only when the account is not frozen and the amount
        does not exceed ``available()``. ``amount`` is assumed already
        validated as a positive int.
        """
        if self.frozen:
            return False
        return amount <= self.available()


@dataclass
class TransactionLog:
    """Append-only record of completed postings.

    Each entry is a tuple ``(account_id, delta_cents)`` where ``delta_cents``
    is positive for a credit and negative for a debit. Order matters: entries
    are appended in the order they are committed.
    """

    entries: list[tuple[str, int]] = field(default_factory=list)

    def record(self, account_id: str, delta: int) -> None:
        self.entries.append((account_id, delta))

    def total_for(self, account_id: str) -> int:
        """Net sum of all deltas recorded for ``account_id`` (0 if none)."""
        return sum(d for a, d in self.entries if a == account_id)
