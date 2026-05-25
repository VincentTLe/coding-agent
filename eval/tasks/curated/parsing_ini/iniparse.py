"""Parse an INI-style configuration string into a nested dict.

Implement ``parse_ini(text)`` that parses an INI configuration and returns a
``dict`` mapping section names to dicts of key/value pairs. Write the parser
yourself; do **not** use ``configparser`` or any other parsing library.

Line types (lines are split on ``"\\n"``; a trailing ``"\\r"`` on any line is
stripped):

  * **Blank line**: a line that is empty or all whitespace. Ignored, EXCEPT it
    terminates any value continuation in progress (see below).
  * **Comment line**: a line whose first non-whitespace character is ``;`` or
    ``#``. Ignored entirely. (``;``/``#`` elsewhere in a line are ordinary
    characters, NOT inline comments.)
  * **Section header**: a line of the form ``[name]`` (optionally surrounded by
    whitespace). ``name`` is stripped of surrounding whitespace and must be
    non-empty. A section name may contain dots, but dots have no special meaning
    here — ``[a.b]`` is a single section literally named ``"a.b"``.
  * **Key/value**: ``key = value`` or ``key : value`` (the first ``=`` or ``:``,
    whichever comes first, is the separator). ``key`` is stripped and must be
    non-empty. ``value`` is stripped of surrounding whitespace.
  * **Continuation**: a line that is indented (starts with a space or tab) and is
    NOT blank/comment/section/key-value-with-separator. It appends to the most
    recent value, joined with a single ``"\\n"``, after stripping the
    continuation line. A continuation with no preceding key in the current
    section is an error.

Type coercion of values (applied to the FINAL joined value string):
  * ``"true"``/``"false"`` (case-insensitive) -> ``True``/``False``.
  * ``"null"``/``"none"`` (case-insensitive) and the empty string ``""`` -> ``None``.
  * An integer literal (optional sign, all digits) -> ``int``.
  * A float literal (parses as float, contains ``.`` / ``e`` / ``E``) -> ``float``.
  * Anything else -> the ``str`` value (continuations keep their ``"\\n"``).
  Multi-line (continued) values are NEVER coerced to bool/int/float/None even if
  every line looks numeric — they stay ``str``.

Sections:
  * Keys appearing BEFORE any section header belong to the default section named
    ``""`` (the empty string). If there are no such keys, there is no ``""`` key
    in the result.
  * A repeated section header merges into the existing section dict.
  * A repeated key within the same section overwrites the earlier value.

Examples:
  parse_ini("[db]\\nhost = localhost\\nport = 5432")
      -> {"db": {"host": "localhost", "port": 5432}}
  parse_ini("debug = true\\n[s]\\nx = 1.5")
      -> {"": {"debug": True}, "s": {"x": 1.5}}
  parse_ini("[a]\\nk = line1\\n    line2")
      -> {"a": {"k": "line1\\nline2"}}

Errors — raise ``ValueError`` for:
  * A malformed section header: ``"["``, ``"[]"``, ``"[a"``, ``"a]"``,
    ``"[a]extra"`` (text after the closing bracket).
  * A non-blank, non-comment, non-section line with no ``=``/``:`` separator that
    is not a valid continuation (e.g. a bare word at column 0, or an indented
    continuation when no key has been seen yet).
  * An empty key (separator with nothing before it, e.g. ``"= value"``).
"""


def parse_ini(text):
    """Parse an INI string and return a nested dict of sections.

    See the module docstring for the full grammar, coercion, and error rules.
    """
    raise NotImplementedError
