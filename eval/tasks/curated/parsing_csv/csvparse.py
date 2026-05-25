"""Parse a CSV document into a list of rows (RFC 4180 style).

Implement ``parse_csv(text)`` that parses an entire CSV document (the string may
contain multiple records) and returns a ``list`` of records, where each record is
a ``list`` of field strings. Write the parser yourself, character by character;
do **not** use the stdlib ``csv`` module.

Format:
  * Fields are separated by commas ``,``.
  * Records are separated by a line terminator: ``"\\n"`` (LF) or ``"\\r\\n"``
    (CRLF). A bare ``"\\r"`` not followed by ``"\\n"`` is NOT a terminator and is
    treated as an ordinary character inside the field.
  * A field may be *quoted* by wrapping it in double quotes ``"``. Inside a quoted
    field:
      - commas, ``"\\n"`` and ``"\\r\\n"`` are literal data (not separators);
      - a literal double quote is written as two double quotes ``""``.
  * An *unquoted* field is the raw run of characters up to the next comma or line
    terminator. Whitespace is significant and is NOT stripped (`" a , b "` ->
    `[" a ", " b "]`).

Examples:
  * ``parse_csv("a,b,c")``            -> ``[["a", "b", "c"]]``
  * ``parse_csv("1,2\\n3,4")``        -> ``[["1", "2"], ["3", "4"]]``
  * ``parse_csv('a,"b,c",d')``        -> ``[["a", "b,c", "d"]]``
  * ``parse_csv('"he said ""hi"""')`` -> ``[['he said "hi"']]``
  * ``parse_csv('"line1\\nline2"')``  -> ``[["line1\\nline2"]]``
  * ``parse_csv("a,,c")``             -> ``[["a", "", "c"]]``

Edge cases (NOT errors):
  * Empty input ``""`` -> ``[]`` (no records).
  * A field may be empty (``"a,,c"`` has an empty middle field).
  * A trailing newline does NOT create an extra empty record:
    ``"a,b\\n"`` -> ``[["a", "b"]]``.
  * A blank line in the middle is a record with a single empty field:
    ``"a\\n\\nb"`` -> ``[["a"], [""], ["b"]]``.
  * Different records may have different numbers of fields (no validation).

Errors — raise ``ValueError`` for malformed quoting:
  * An unterminated quoted field (opening quote with no closing quote before
    end of input), e.g. ``'"abc'``.
  * A quote that appears in the middle of an *unquoted* field, e.g. ``'ab"c'``
    (a field is only quoted if it *starts* with a quote).
  * Characters after a closing quote other than a comma or line terminator,
    e.g. ``'"ab"c'`` or ``'"ab" ,c'``.
"""


def parse_csv(text):
    """Parse a CSV document string into a list of rows (lists of fields).

    See the module docstring for the exact format and error rules.
    """
    raise NotImplementedError
