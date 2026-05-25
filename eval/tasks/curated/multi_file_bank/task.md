# multi_file_bank — Bank transfer & overdraft service

## Goal
Implement the `Bank` service in `bank.py` so all tests in `test_bank.py` pass.

The domain models are already written for you in `models.py` (an `Account`
dataclass, a `TransactionLog`, and a `BankError` exception hierarchy). You
MUST read `models.py` to implement `bank.py` correctly — the rules about
money units, overdraft, frozen accounts, and the exception types all live
there, and your service should reuse those helpers rather than re-derive them.

Money is always an integer number of **cents** — never use floats.

Implement these `Bank` methods (full specs are in the `bank.py` docstrings):

- `open_account(account_id, *, overdraft_limit=0)` — register a new zero-balance
  account. Reject a duplicate id or a negative overdraft limit with `ValueError`.
- `get(account_id)` — return the account or raise `AccountNotFound`.
- `deposit(account_id, amount)` — credit the account. `amount` must be a
  positive `int` (reject `bool`) or raise `InvalidAmount`. Frozen accounts may
  still receive deposits. Record a `+amount` entry in the log.
- `withdraw(account_id, amount)` — debit the account. Validate the amount
  first (`InvalidAmount`), then reject frozen accounts (`AccountFrozen`), then
  reject debits over the available balance, i.e. `balance + overdraft_limit`
  (`InsufficientFunds`). Record a `-amount` entry on success.
- `transfer(src_id, dst_id, amount)` — move money atomically. Both accounts
  must exist; the ids must differ (`ValueError`). If the source debit cannot
  proceed, NO balance changes and NOTHING is written to the log. On success
  the log gains exactly the source debit followed by the destination credit.
- `net_position()` — sum of all account balances in cents.

Example:

```python
b = Bank()
b.open_account("alice")
b.open_account("bob", overdraft_limit=500)
b.deposit("alice", 1000)
b.transfer("alice", "bob", 300)
# alice.balance == 700, bob.balance == 300
# log entries end with [("alice", -300), ("bob", 300)]
```

## Category
multi_file

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
