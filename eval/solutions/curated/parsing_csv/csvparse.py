"""Parse a CSV document into a list of rows (RFC 4180 style) — reference.

Character-by-character state machine. We parse one field at a time; a field is
followed by exactly one of: a comma (more fields in this row), a line terminator
(end of row), or end-of-input (end of row + end of document).
"""


def parse_csv(text):
    if not isinstance(text, str):
        raise ValueError("input must be a string")

    rows = []
    n = len(text)
    if n == 0:
        return rows

    i = 0
    row = []
    while True:
        # --- parse one field starting at index i -------------------------
        field_chars = []
        if i < n and text[i] == '"':
            # Quoted field.
            i += 1
            while True:
                if i >= n:
                    raise ValueError("unterminated quoted field")
                ch = text[i]
                if ch == '"':
                    # Either an escaped quote ("") or the closing quote.
                    if i + 1 < n and text[i + 1] == '"':
                        field_chars.append('"')
                        i += 2
                    else:
                        i += 1  # consume closing quote
                        break
                else:
                    field_chars.append(ch)
                    i += 1
            # After a closing quote, only a comma, line terminator, or EOF
            # may follow.
            if i < n and text[i] not in (",", "\n", "\r"):
                raise ValueError("unexpected text after closing quote")
        else:
            # Unquoted field: read until comma, LF, or CRLF.
            while i < n:
                ch = text[i]
                if ch == ",":
                    break
                if ch == "\n":
                    break
                if ch == "\r" and i + 1 < n and text[i + 1] == "\n":
                    break
                if ch == '"':
                    raise ValueError("unexpected quote in unquoted field")
                field_chars.append(ch)
                i += 1

        row.append("".join(field_chars))

        # --- decide what ends the field ----------------------------------
        if i >= n:
            rows.append(row)
            break
        ch = text[i]
        if ch == ",":
            i += 1
            continue  # next field in same row
        if ch == "\n":
            i += 1
            rows.append(row)
            row = []
            if i >= n:
                # Trailing newline: do NOT emit a trailing empty record.
                break
            continue
        if ch == "\r" and i + 1 < n and text[i + 1] == "\n":
            i += 2
            rows.append(row)
            row = []
            if i >= n:
                break
            continue
        # Should be unreachable: the field readers stop only on , \n \r\n EOF.
        raise ValueError(f"unexpected character {ch!r}")

    return rows
