"""Tests for bank.py. Visible — use them as feedback while implementing."""

import pytest

from bank import Bank
from models import (
    AccountFrozen,
    AccountNotFound,
    InsufficientFunds,
    InvalidAmount,
)


def make_bank():
    b = Bank()
    b.open_account("alice")
    b.open_account("bob", overdraft_limit=500)
    b.deposit("alice", 1000)
    return b


def test_open_and_get():
    b = Bank()
    acct = b.open_account("x")
    assert acct.balance == 0
    assert acct.overdraft_limit == 0
    assert b.get("x") is acct


def test_open_duplicate_rejected():
    b = Bank()
    b.open_account("x")
    with pytest.raises(ValueError):
        b.open_account("x")


def test_open_negative_overdraft_rejected():
    b = Bank()
    with pytest.raises(ValueError):
        b.open_account("x", overdraft_limit=-1)


def test_get_unknown_raises():
    b = Bank()
    with pytest.raises(AccountNotFound):
        b.get("ghost")


def test_deposit_increases_balance_and_logs():
    b = make_bank()
    b.deposit("alice", 250)
    assert b.get("alice").balance == 1250
    assert b.log.total_for("alice") == 1250  # 1000 + 250


def test_deposit_into_frozen_ok():
    b = make_bank()
    b.get("alice").frozen = True
    b.deposit("alice", 100)
    assert b.get("alice").balance == 1100


@pytest.mark.parametrize("bad", [0, -5, 3.0, "10", None, True])
def test_deposit_invalid_amount(bad):
    # NOTE: True is an int subclass but must be rejected as a money amount.
    b = make_bank()
    with pytest.raises(InvalidAmount):
        b.deposit("alice", bad)


def test_withdraw_basic():
    b = make_bank()
    b.withdraw("alice", 400)
    assert b.get("alice").balance == 600
    assert b.log.entries[-1] == ("alice", -400)


def test_withdraw_to_exact_zero():
    b = make_bank()
    b.withdraw("alice", 1000)
    assert b.get("alice").balance == 0


def test_withdraw_insufficient():
    b = make_bank()
    with pytest.raises(InsufficientFunds):
        b.withdraw("alice", 1001)  # no overdraft on alice
    assert b.get("alice").balance == 1000  # unchanged


def test_withdraw_uses_overdraft():
    b = make_bank()
    b.deposit("bob", 100)          # bob balance 100, overdraft 500 -> avail 600
    b.withdraw("bob", 600)
    assert b.get("bob").balance == -500
    # one cent more is over the limit
    with pytest.raises(InsufficientFunds):
        b.withdraw("bob", 1)


def test_withdraw_frozen_raises_before_funds_check():
    b = make_bank()
    b.get("alice").frozen = True
    # Frozen must be reported even though funds are sufficient.
    with pytest.raises(AccountFrozen):
        b.withdraw("alice", 100)


def test_withdraw_invalid_amount_checked_first():
    b = make_bank()
    b.get("alice").frozen = True
    # amount validity is checked before the frozen check
    with pytest.raises(InvalidAmount):
        b.withdraw("alice", -1)


def test_transfer_moves_funds_and_logs_in_order():
    b = make_bank()
    before = len(b.log.entries)
    b.transfer("alice", "bob", 300)
    assert b.get("alice").balance == 700
    assert b.get("bob").balance == 300
    assert b.log.entries[before:] == [("alice", -300), ("bob", 300)]


def test_transfer_unknown_account():
    b = make_bank()
    with pytest.raises(AccountNotFound):
        b.transfer("alice", "nobody", 100)
    with pytest.raises(AccountNotFound):
        b.transfer("nobody", "alice", 100)


def test_transfer_to_self_rejected():
    b = make_bank()
    with pytest.raises(ValueError):
        b.transfer("alice", "alice", 100)


def test_transfer_atomic_on_insufficient_funds():
    b = make_bank()
    log_len = len(b.log.entries)
    with pytest.raises(InsufficientFunds):
        b.transfer("alice", "bob", 5000)  # alice only has 1000
    # nothing moved, nothing logged
    assert b.get("alice").balance == 1000
    assert b.get("bob").balance == 0
    assert len(b.log.entries) == log_len


def test_transfer_atomic_on_frozen_source():
    b = make_bank()
    b.get("alice").frozen = True
    log_len = len(b.log.entries)
    with pytest.raises(AccountFrozen):
        b.transfer("alice", "bob", 100)
    assert b.get("alice").balance == 1000
    assert b.get("bob").balance == 0
    assert len(b.log.entries) == log_len


def test_transfer_into_frozen_destination_ok():
    b = make_bank()
    b.get("bob").frozen = True  # frozen blocks debits, not credits
    b.transfer("alice", "bob", 200)
    assert b.get("alice").balance == 800
    assert b.get("bob").balance == 200


def test_net_position():
    b = make_bank()
    # alice 1000, bob 0
    assert b.net_position() == 1000
    b.withdraw("bob", 300)  # uses overdraft -> bob -300
    assert b.net_position() == 700
