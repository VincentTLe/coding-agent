"""Minimal CSV parsing + numeric column summation (hand-rolled, stdlib only).

`parse_line` splits ONE line of CSV into a list of field strings. It follows the
usual quoting rules:
  - A field may be wrapped in double quotes; commas inside quotes are literal,
    so `"Smith, John",10` parses to ['Smith, John', '10'].
  - A doubled quote inside a quoted field is a literal quote character, e.g.
    the 5-char field `"a""b"` parses to the 3-char value a"b (one quote in the
    middle).
  - The surrounding quotes are not part of the value.

`sum_column(text, column)` takes a full CSV document whose first line is a
header row, finds `column` by name, and returns the sum (as float) of the
numeric values in that column over the remaining data rows. Blank lines are
ignored. Values may be integers or decimals ("100.50" contributes 100.5).
"""


def parse_line(line: str) -> list[str]:
    """Split a single CSV line into fields, honouring double-quoted fields."""
    fields: list[str] = []
    cur: list[str] = []
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quotes:
            if ch == '"':
                # A doubled quote ("") inside quotes is one literal quote.
                if i + 1 < len(line) and line[i + 1] == '"':
                    cur.append('"')
                    i += 2
                    continue
                in_quotes = False
                i += 1
                continue
            cur.append(ch)
            i += 1
        else:
            if ch == '"':
                in_quotes = True
                i += 1
            elif ch == ",":
                fields.append("".join(cur))
                cur = []
                i += 1
            else:
                cur.append(ch)
                i += 1
    fields.append("".join(cur))
    return fields


def sum_column(text: str, column: str) -> float:
    """Sum the numeric values of the named column across all data rows."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("no data")
    header = parse_line(lines[0])
    idx = header.index(column)
    total = 0.0
    for ln in lines[1:]:
        row = parse_line(ln)
        total += float(row[idx])
    return total
