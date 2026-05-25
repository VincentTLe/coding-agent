import pytest

from iniparse import parse_ini


# ----------------------------- basic sections ------------------------------

def test_single_section():
    assert parse_ini("[db]\nhost = localhost") == {"db": {"host": "localhost"}}


def test_multiple_sections():
    text = "[a]\nx = 1\n[b]\ny = 2"
    assert parse_ini(text) == {"a": {"x": 1}, "b": {"y": 2}}


def test_colon_separator():
    assert parse_ini("[s]\nkey : value") == {"s": {"key": "value"}}


def test_first_separator_wins():
    # The first '=' or ':' splits; the rest is value.
    assert parse_ini("[s]\nurl = http://x:8080/p") == {"s": {"url": "http://x:8080/p"}}
    assert parse_ini("[s]\na = b=c=d") == {"s": {"a": "b=c=d"}}


def test_whitespace_around_key_and_value_stripped():
    assert parse_ini("[s]\n  key   =   value  ") == {"s": {"key": "value"}}


def test_whitespace_around_section_name():
    assert parse_ini("[  s  ]\nk = v") == {"s": {"k": "v"}}


# ----------------------------- default section -----------------------------

def test_default_section_for_leading_keys():
    assert parse_ini("debug = true\n[s]\nx = 1") == {"": {"debug": True}, "s": {"x": 1}}


def test_no_default_section_when_no_leading_keys():
    result = parse_ini("[s]\nx = 1")
    assert "" not in result
    assert result == {"s": {"x": 1}}


# ----------------------------- comments & blanks ---------------------------

def test_semicolon_comment_ignored():
    text = "; a comment\n[s]\nk = v"
    assert parse_ini(text) == {"s": {"k": "v"}}


def test_hash_comment_ignored():
    text = "[s]\n# comment here\nk = v"
    assert parse_ini(text) == {"s": {"k": "v"}}


def test_indented_comment_ignored():
    text = "[s]\nk = v\n   ; indented comment\nj = w"
    assert parse_ini(text) == {"s": {"k": "v", "j": "w"}}


def test_blank_lines_ignored():
    text = "\n\n[s]\n\nk = v\n\n"
    assert parse_ini(text) == {"s": {"k": "v"}}


def test_hash_and_semicolon_inside_value_are_literal():
    assert parse_ini("[s]\na = x ; y") == {"s": {"a": "x ; y"}}
    assert parse_ini("[s]\nb = c # d") == {"s": {"b": "c # d"}}


def test_crlf_line_endings():
    text = "[s]\r\nk = v\r\nj = w\r\n"
    assert parse_ini(text) == {"s": {"k": "v", "j": "w"}}


# ----------------------------- type coercion -------------------------------

def test_int_coercion():
    assert parse_ini("[s]\na = 42\nb = -7\nc = +3") == {"s": {"a": 42, "b": -7, "c": 3}}


def test_float_coercion():
    got = parse_ini("[s]\na = 1.5\nb = -0.25\nc = 2e3")
    assert got == {"s": {"a": 1.5, "b": -0.25, "c": 2000.0}}
    assert isinstance(got["s"]["a"], float)


def test_bool_coercion_case_insensitive():
    got = parse_ini("[s]\na = true\nb = False\nc = TRUE")
    assert got == {"s": {"a": True, "b": False, "c": True}}


def test_none_coercion():
    got = parse_ini("[s]\na = null\nb = None\nc = NONE\nd =")
    assert got == {"s": {"a": None, "b": None, "c": None, "d": None}}


def test_string_values_left_alone():
    got = parse_ini("[s]\na = hello\nb = 3 apples\nc = 1.2.3")
    assert got == {"s": {"a": "hello", "b": "3 apples", "c": "1.2.3"}}


def test_numeric_looking_with_letters_is_string():
    assert parse_ini("[s]\na = 12abc") == {"s": {"a": "12abc"}}


# ----------------------------- continuations -------------------------------

def test_simple_continuation():
    text = "[a]\nk = line1\n    line2"
    assert parse_ini(text) == {"a": {"k": "line1\nline2"}}


def test_multiple_continuation_lines():
    text = "[a]\nk = one\n  two\n\tthree"
    assert parse_ini(text) == {"a": {"k": "one\ntwo\nthree"}}


def test_continuation_stops_at_blank_line():
    text = "[a]\nk = one\n  two\n\n  three = 3"
    # blank line ends the continuation; "three = 3" is a normal key/value.
    assert parse_ini(text) == {"a": {"k": "one\ntwo", "three": 3}}


def test_continuation_stops_at_next_key():
    text = "[a]\nk = one\n  two\nj = v"
    assert parse_ini(text) == {"a": {"k": "one\ntwo", "j": "v"}}


def test_multiline_value_not_coerced():
    # Even though both lines are numeric, a continued value stays a string.
    text = "[a]\nk = 1\n  2"
    assert parse_ini(text) == {"a": {"k": "1\n2"}}


# ----------------------------- merging / overwrite -------------------------

def test_repeated_section_merges():
    text = "[a]\nx = 1\n[b]\ny = 2\n[a]\nz = 3"
    assert parse_ini(text) == {"a": {"x": 1, "z": 3}, "b": {"y": 2}}


def test_repeated_key_overwrites():
    text = "[a]\nx = 1\nx = 2"
    assert parse_ini(text) == {"a": {"x": 2}}


def test_dotted_section_name_is_literal():
    assert parse_ini("[a.b.c]\nk = v") == {"a.b.c": {"k": "v"}}


# ----------------------------- empty input ---------------------------------

def test_empty_input():
    assert parse_ini("") == {}


def test_only_comments_and_blanks():
    assert parse_ini("; just a comment\n\n# another\n") == {}


# ----------------------------- error cases ---------------------------------

def test_unclosed_section_raises():
    with pytest.raises(ValueError):
        parse_ini("[a\nk = v")


def test_empty_section_name_raises():
    with pytest.raises(ValueError):
        parse_ini("[]\nk = v")


def test_text_after_closing_bracket_raises():
    with pytest.raises(ValueError):
        parse_ini("[a]extra\nk = v")


def test_lone_close_bracket_raises():
    with pytest.raises(ValueError):
        parse_ini("a]\nk = v")


def test_lone_open_bracket_raises():
    with pytest.raises(ValueError):
        parse_ini("[")


def test_bare_word_no_separator_raises():
    with pytest.raises(ValueError):
        parse_ini("[s]\njustaword")


def test_empty_key_raises():
    with pytest.raises(ValueError):
        parse_ini("[s]\n= value")


def test_continuation_with_no_preceding_key_raises():
    # Indented value-looking line as the first content line of a section.
    with pytest.raises(ValueError):
        parse_ini("[s]\n   orphan continuation")


def test_value_may_contain_close_bracket():
    # Regression: a value ending in ']' must NOT be treated as a section header.
    assert parse_ini("[s]\nk = arr]") == {"s": {"k": "arr]"}}
