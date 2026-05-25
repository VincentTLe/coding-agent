import pytest

from jsonmini import parse


# ----------------------------- literals ------------------------------------

def test_true_false_null():
    assert parse("true") is True
    assert parse("false") is False
    assert parse("null") is None


def test_literals_with_whitespace():
    assert parse("   true   ") is True
    assert parse("\n\tnull\n") is None


# ----------------------------- numbers -------------------------------------

def test_integers():
    assert parse("0") == 0
    assert parse("42") == 42
    assert parse("-7") == -7
    assert isinstance(parse("42"), int)
    assert isinstance(parse("-7"), int)


def test_floats():
    assert parse("3.14") == 3.14
    assert parse("-0.5") == -0.5
    assert isinstance(parse("3.14"), float)


def test_exponent_numbers_are_floats():
    assert parse("1e3") == 1000.0
    assert parse("2E-2") == 0.02
    assert parse("1.5e2") == 150.0
    assert isinstance(parse("1e3"), float)


def test_zero_variants():
    assert parse("0") == 0
    assert parse("-0") == 0
    assert parse("0.0") == 0.0


# ----------------------------- strings -------------------------------------

def test_simple_string():
    assert parse('"hello"') == "hello"
    assert parse('""') == ""


def test_string_with_spaces_and_unicode_text():
    assert parse('"hello world"') == "hello world"
    assert parse('"caf\\u00e9"') == "café"


def test_string_escapes():
    assert parse('"a\\nb"') == "a\nb"
    assert parse('"tab\\there"') == "tab\there"
    assert parse('"quote\\"inside"') == 'quote"inside'
    assert parse('"back\\\\slash"') == "back\\slash"
    assert parse('"slash\\/end"') == "slash/end"


def test_unicode_escape_value():
    assert parse('"\\u0041\\u0042"') == "AB"


# ----------------------------- arrays --------------------------------------

def test_empty_array():
    assert parse("[]") == []
    assert parse("  [  ]  ") == []


def test_flat_array():
    assert parse("[1, 2, 3]") == [1, 2, 3]
    assert parse("[true, false, null]") == [True, False, None]
    assert parse('["a", "b"]') == ["a", "b"]


def test_mixed_array():
    assert parse('[1, "two", 3.0, true, null]') == [1, "two", 3.0, True, None]


def test_nested_array():
    assert parse("[[1, 2], [3, [4, 5]]]") == [[1, 2], [3, [4, 5]]]


# ----------------------------- objects -------------------------------------

def test_empty_object():
    assert parse("{}") == {}
    assert parse("  {  }  ") == {}


def test_flat_object():
    assert parse('{"a": 1, "b": 2}') == {"a": 1, "b": 2}


def test_object_value_types():
    assert parse('{"x": true, "y": null, "z": "s"}') == {"x": True, "y": None, "z": "s"}


def test_nested_object():
    got = parse('{"outer": {"inner": [1, 2], "flag": false}}')
    assert got == {"outer": {"inner": [1, 2], "flag": False}}


def test_object_with_whitespace_everywhere():
    got = parse('{\n  "a" : 1 ,\n  "b" : [ 2 , 3 ]\n}')
    assert got == {"a": 1, "b": [2, 3]}


def test_duplicate_keys_last_wins():
    assert parse('{"a": 1, "a": 2}') == {"a": 2}


def test_deeply_nested_structure():
    text = '{"users": [{"id": 1, "tags": ["x", "y"]}, {"id": 2, "tags": []}]}'
    assert parse(text) == {
        "users": [
            {"id": 1, "tags": ["x", "y"]},
            {"id": 2, "tags": []},
        ]
    }


# ----------------------------- error: empty --------------------------------

def test_empty_input_raises():
    with pytest.raises(ValueError):
        parse("")
    with pytest.raises(ValueError):
        parse("    ")


# ----------------------------- error: trailing content ---------------------

def test_trailing_content_raises():
    with pytest.raises(ValueError):
        parse("1 2")
    with pytest.raises(ValueError):
        parse("{} []")
    with pytest.raises(ValueError):
        parse('"a" "b"')
    with pytest.raises(ValueError):
        parse("true false")


# ----------------------------- error: trailing commas ----------------------

def test_trailing_comma_in_array_raises():
    with pytest.raises(ValueError):
        parse("[1, 2,]")
    with pytest.raises(ValueError):
        parse("[,]")


def test_trailing_comma_in_object_raises():
    with pytest.raises(ValueError):
        parse('{"a": 1,}')


# ----------------------------- error: structure ----------------------------

def test_missing_comma_raises():
    with pytest.raises(ValueError):
        parse("[1 2]")
    with pytest.raises(ValueError):
        parse('{"a": 1 "b": 2}')


def test_missing_colon_raises():
    with pytest.raises(ValueError):
        parse('{"a" 1}')


def test_unquoted_key_raises():
    with pytest.raises(ValueError):
        parse("{a: 1}")


def test_single_quoted_string_raises():
    with pytest.raises(ValueError):
        parse("'hello'")
    with pytest.raises(ValueError):
        parse("{'a': 1}")


def test_unterminated_string_raises():
    with pytest.raises(ValueError):
        parse('"abc')


def test_unterminated_array_raises():
    with pytest.raises(ValueError):
        parse("[1, 2")


def test_unterminated_object_raises():
    with pytest.raises(ValueError):
        parse('{"a": 1')


# ----------------------------- error: literals -----------------------------

def test_unknown_literals_raise():
    with pytest.raises(ValueError):
        parse("True")
    with pytest.raises(ValueError):
        parse("NULL")
    with pytest.raises(ValueError):
        parse("undefined")
    with pytest.raises(ValueError):
        parse("nul")


# ----------------------------- error: bad numbers --------------------------

def test_leading_zero_raises():
    with pytest.raises(ValueError):
        parse("01")
    with pytest.raises(ValueError):
        parse("-01")


def test_bare_minus_raises():
    with pytest.raises(ValueError):
        parse("-")


def test_leading_or_trailing_dot_raises():
    with pytest.raises(ValueError):
        parse(".5")
    with pytest.raises(ValueError):
        parse("5.")
    with pytest.raises(ValueError):
        parse("1.")


def test_leading_plus_raises():
    with pytest.raises(ValueError):
        parse("+1")


def test_bad_exponent_raises():
    with pytest.raises(ValueError):
        parse("1e")
    with pytest.raises(ValueError):
        parse("1e+")


# ----------------------------- error: bad escapes --------------------------

def test_bad_escape_raises():
    with pytest.raises(ValueError):
        parse('"bad\\xescape"')
    with pytest.raises(ValueError):
        parse('"\\"')  # lone backslash then closing quote consumed as escape


def test_bad_unicode_escape_raises():
    with pytest.raises(ValueError):
        parse('"\\u12"')
    with pytest.raises(ValueError):
        parse('"\\uZZZZ"')


def test_raw_control_char_in_string_raises():
    with pytest.raises(ValueError):
        parse('"line\nbreak"')  # raw newline inside string is invalid
