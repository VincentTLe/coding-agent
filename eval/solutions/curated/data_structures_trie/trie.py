"""Reference solution for the Trie task.

Each node holds a dict of child-char -> node and a flag marking the end of an
inserted word. Deletion prunes nodes that become both childless and non-final.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class _Node:
    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: Dict[str, "_Node"] = {}
        self.is_word: bool = False


class Trie:
    def __init__(self) -> None:
        self._root = _Node()
        self._count = 0

    def _find(self, prefix: str) -> Optional[_Node]:
        node = self._root
        for ch in prefix:
            nxt = node.children.get(ch)
            if nxt is None:
                return None
            node = nxt
        return node

    def insert(self, word: str) -> None:
        node = self._root
        for ch in word:
            node = node.children.setdefault(ch, _Node())
        if not node.is_word:
            node.is_word = True
            self._count += 1

    def search(self, word: str) -> bool:
        node = self._find(word)
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        # True iff some inserted word has this prefix. On a non-empty trie the
        # reached node always has a word in its subtree (dangling nodes are
        # pruned on delete); the empty-trie / empty-prefix corner is False.
        if self._count == 0:
            return False
        return self._find(prefix) is not None

    def delete(self, word: str) -> bool:
        # Walk down recording the path so we can prune on the way back up.
        path = [self._root]
        node = self._root
        for ch in word:
            nxt = node.children.get(ch)
            if nxt is None:
                return False
            path.append(nxt)
            node = nxt
        if not node.is_word:
            return False
        node.is_word = False
        self._count -= 1
        # Prune: remove childless, non-word nodes from the leaf upward.
        for i in range(len(word) - 1, -1, -1):
            child = path[i + 1]
            if child.children or child.is_word:
                break
            del path[i].children[word[i]]
        return True

    def words_with_prefix(self, prefix: str) -> List[str]:
        start = self._find(prefix)
        if start is None:
            return []
        out: List[str] = []
        self._collect(start, prefix, out)
        out.sort()
        return out

    def _collect(self, node: _Node, acc: str, out: List[str]) -> None:
        if node.is_word:
            out.append(acc)
        for ch, child in node.children.items():
            self._collect(child, acc + ch, out)

    def __len__(self) -> int:
        return self._count
