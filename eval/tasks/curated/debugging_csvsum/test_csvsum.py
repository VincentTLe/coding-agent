"""Tests for csvsum.py. Currently RED until the planted bugs are fixed."""

import pytest

from csvsum import parse_line, sum_column


def test_parse_plain():
    assert parse_line("a,b,c") == ["a", "b", "c"]
    assert parse_line("1,2,3") == ["1", "2", "3"]


def test_parse_empty_fields():
    assert parse_line("a,,c") == ["a", "", "c"]
    assert parse_line("") == [""]


def test_parse_quoted_comma():
    # Commas inside quotes are literal; surrounding quotes are stripped.
    assert parse_line('"Smith, John",10') == ["Smith, John", "10"]
    assert parse_line('x,"a,b,c",y') == ["x", "a,b,c", "y"]


def test_parse_escaped_quote():
    # A doubled quote inside a quoted field is one literal quote character.
    assert parse_line('"a""b"') == ['a"b']
    assert parse_line('"say ""hi"""') == ['say "hi"']
    assert parse_line('1,"He said ""go""",2') == ["1", 'He said "go"', "2"]


def test_sum_column_integers():
    text = "name,amount\nA,10\nB,20\nC,30"
    assert sum_column(text, "amount") == 60.0


def test_sum_column_decimals():
    text = "item,price\napple,100.50\npear,0.25\nplum,9.25"
    assert sum_column(text, "price") == pytest.approx(110.0)


def test_sum_column_with_quoted_commas():
    # Quoted names contain commas; the amount column must stay aligned.
    text = (
        "name,amount\n"
        '"Doe, Jane",100.5\n'
        '"Smith, John",200.5\n'
        "Plainname,99\n"
    )
    assert sum_column(text, "amount") == pytest.approx(400.0)


def test_sum_column_ignores_blank_lines():
    text = "x,y\n1,5\n\n2,15\n\n"
    assert sum_column(text, "y") == pytest.approx(20.0)
