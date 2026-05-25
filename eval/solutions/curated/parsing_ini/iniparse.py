"""Parse an INI-style configuration string into a nested dict — reference.

Line-oriented parser. Raw (string) values are accumulated first so that
continuation lines can extend a value; type coercion is applied last, and only
to single-line values.
"""


def _coerce(raw):
    """Coerce a single-line raw value string to bool/int/float/None/str."""
    low = raw.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if raw == "" or low in ("null", "none"):
        return None
    # int literal: optional sign then all digits.
    body = raw[1:] if raw[:1] in "+-" else raw
    if body.isdigit() and body != "":
        return int(raw)
    # float literal: must look floaty (dot/exp) and parse cleanly.
    if any(c in raw for c in ".eE"):
        try:
            return float(raw)
        except ValueError:
            return raw
    return raw


def parse_ini(text):
    if not isinstance(text, str):
        raise ValueError("input must be a string")

    sections = {}            # name -> {key: raw_value_str}
    multiline = set()        # (section_name, key) that received continuations
    cur_section = None       # None until first key or section; "" = default
    last_key = None          # last key written, for continuations

    def ensure_default():
        nonlocal cur_section
        if cur_section is None:
            cur_section = ""
            sections.setdefault("", {})

    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\r")
        stripped = line.strip()

        # Blank line: ends any continuation in progress.
        if stripped == "":
            last_key = None
            continue

        # Comment line.
        if stripped[0] in (";", "#"):
            last_key = None
            continue

        # Section header.
        if stripped[0] == "[":
            if not stripped.endswith("]"):
                raise ValueError(f"malformed section header: {line!r}")
            name = stripped[1:-1].strip()
            if name == "":
                raise ValueError("empty section name")
            cur_section = name
            sections.setdefault(name, {})
            last_key = None
            continue

        # Continuation: indented line that is not a key/value pair.
        is_indented = line[:1] in (" ", "\t")
        eq = line.find("=")
        co = line.find(":")
        seps = [p for p in (eq, co) if p != -1]
        has_sep = bool(seps)

        # A line with no separator that ends in ']' but has no opener (e.g.
        # "a]") is a malformed section header. Checked only when there is no
        # key/value separator so that values may legitimately contain ']'.
        if not has_sep and stripped.endswith("]") and "[" not in stripped:
            raise ValueError(f"malformed section header: {line!r}")

        if is_indented and not has_sep:
            if cur_section is None or last_key is None:
                raise ValueError(f"continuation with no preceding key: {line!r}")
            prev = sections[cur_section][last_key]
            sections[cur_section][last_key] = prev + "\n" + stripped
            multiline.add((cur_section, last_key))
            continue

        # Key/value pair.
        if not has_sep:
            raise ValueError(f"line is not a section, comment or key/value: {line!r}")
        sep = min(seps)
        key = line[:sep].strip()
        value = line[sep + 1:].strip()
        if key == "":
            raise ValueError(f"empty key in line: {line!r}")
        ensure_default()
        sections[cur_section][key] = value
        last_key = key

    # Final coercion pass.
    result = {}
    for sec, kv in sections.items():
        out = {}
        for key, raw in kv.items():
            if (sec, key) in multiline:
                out[key] = raw          # multi-line values stay strings
            else:
                out[key] = _coerce(raw)
        result[sec] = out
    return result
