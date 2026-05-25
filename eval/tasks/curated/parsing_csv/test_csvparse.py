import pytest

from csvparse import parse_csv


# ----------------------------- basic rows ----------------------------------

def test_single_row():
    assert parse_csv("a,b,c") == [["a", "b", "c"]]


def test_single_field():
    assert parse_csv("hello") == [["hello"]]


def test_multiple_rows_lf():
    assert parse_csv("1,2\n3,4") == [["1", "2"], ["3", "4"]]


def test_multiple_rows_crlf():
    assert parse_csv("1,2\r\n3,4\r\n5,6") == [["1", "2"], ["3", "4"], ["5", "6"]]


def test_mixed_lf_and_crlf_terminators():
    assert parse_csv("a,b\nc,d\r\ne,f") == [["a", "b"], ["c", "d"], ["e", "f"]]


# ----------------------------- empty / blank fields ------------------------

def test_empty_input():
    assert parse_csv("") == []


def test_empty_middle_field():
    assert parse_csv("a,,c") == [["a", "", "c"]]


def test_empty_leading_and_trailing_fields():
    assert parse_csv(",a,") == [["", "a", ""]]


def test_all_empty_fields():
    assert parse_csv(",,") == [["", "", ""]]


# ----------------------------- trailing / blank lines ----------------------

def test_trailing_lf_no_extra_row():
    assert parse_csv("a,b\n") == [["a", "b"]]


def test_trailing_crlf_no_extra_row():
    assert parse_csv("a,b\r\n") == [["a", "b"]]


def test_blank_line_in_middle():
    assert parse_csv("a\n\nb") == [["a"], [""], ["b"]]


def test_ragged_rows_allowed():
    assert parse_csv("a,b,c\nx,y") == [["a", "b", "c"], ["x", "y"]]


# ----------------------------- whitespace significance ---------------------

def test_whitespace_is_significant():
    assert parse_csv(" a , b ") == [[" a ", " b "]]


def test_tabs_preserved():
    assert parse_csv("a\t,b") == [["a\t", "b"]]


# ----------------------------- quoted fields -------------------------------

def test_quoted_simple():
    assert parse_csv('"a","b"') == [["a", "b"]]


def test_quoted_embedded_comma():
    assert parse_csv('a,"b,c",d') == [["a", "b,c", "d"]]


def test_quoted_embedded_newline_lf():
    assert parse_csv('"line1\nline2"') == [["line1\nline2"]]


def test_quoted_embedded_newline_crlf():
    assert parse_csv('"line1\r\nline2",x') == [["line1\r\nline2", "x"]]


def test_quoted_escaped_quotes():
    assert parse_csv('"he said ""hi"""') == [['he said "hi"']]


def test_quoted_field_that_is_only_escaped_quote():
    assert parse_csv('""""') == [['"']]


def test_quoted_empty_field():
    assert parse_csv('"",a') == [["", "a"]]


def test_quoted_whitespace_preserved():
    assert parse_csv('"  spaced  "') == [["  spaced  "]]


def test_mix_quoted_and_unquoted_across_rows():
    text = 'name,note\n"Smith, John","says ""hi"""\nDoe,plain'
    assert parse_csv(text) == [
        ["name", "note"],
        ["Smith, John", 'says "hi"'],
        ["Doe", "plain"],
    ]


def test_bare_carriage_return_is_data():
    # A lone \r not followed by \n is an ordinary character, not a terminator.
    assert parse_csv("a\rb,c") == [["a\rb", "c"]]


def test_quoted_field_with_bare_cr():
    assert parse_csv('"a\rb"') == [["a\rb"]]


# ----------------------------- error: bad quoting --------------------------

def test_unterminated_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"abc')


def test_unterminated_quote_after_escape_raises():
    with pytest.raises(ValueError):
        parse_csv('"ab""')  # the "" is an escaped quote, then field never closes


def test_quote_in_middle_of_unquoted_field_raises():
    with pytest.raises(ValueError):
        parse_csv('ab"c')


def test_text_after_closing_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"ab"c')


def test_space_after_closing_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"ab" ,c')


def test_unterminated_quote_in_second_field_raises():
    with pytest.raises(ValueError):
        parse_csv('a,"bc')


def test_unterminated_quote_in_second_row_raises():
    with pytest.raises(ValueError):
        parse_csv('a,b\n"oops')
