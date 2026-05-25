"""Prefix tree (Trie) — implement-from-spec stub.

Replace every ``raise NotImplementedError`` with a working implementation that
satisfies the contract on each method and in task.md.
"""

from __future__ import annotations

from typing import List


class Trie:
    """A prefix tree storing a set of strings (the empty string allowed).

    A word is "present" only if it was explicitly inserted. Prefix queries
    succeed for any inserted word's prefix, including the full word itself.
    Operations are case-sensitive and may receive any unicode characters.
    """

    def __init__(self) -> None:
        """Create an empty trie containing no words."""
        raise NotImplementedError

    def insert(self, word: str) -> None:
        """Add ``word`` to the trie. Inserting the same word twice is a no-op
        (idempotent) and must not change ``__len__`` the second time.
        """
        raise NotImplementedError

    def search(self, word: str) -> bool:
        """Return True iff ``word`` was inserted as a complete word."""
        raise NotImplementedError

    def starts_with(self, prefix: str) -> bool:
        """Return True iff some inserted word starts with ``prefix``.

        Every inserted word is a prefix of itself. The empty string is a prefix
        of every word, so ``starts_with("")`` is True whenever the trie is
        non-empty.
        """
        raise NotImplementedError

    def delete(self, word: str) -> bool:
        """Remove ``word`` if present. Return True if a word was removed, False
        if it was absent. Removing a word must not break unrelated words that
        share a prefix with it, and dangling nodes should be pruned so that
        ``starts_with`` no longer reports the removed-only prefix.
        """
        raise NotImplementedError

    def words_with_prefix(self, prefix: str) -> List[str]:
        """Return all inserted words that start with ``prefix``, sorted
        lexicographically (ascending). If ``prefix`` matches nothing, return an
        empty list. ``prefix=""`` returns every word in the trie, sorted.
        """
        raise NotImplementedError

    def __len__(self) -> int:
        """Return the number of distinct words currently stored."""
        raise NotImplementedError
