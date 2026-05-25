from tokenizer import tokenize


def test_simple_split():
    assert tokenize("a, b,c") == ["a", "b", "c"]


def test_consecutive_delimiters_collapse():
    # No empty tokens from runs of delimiters.
    assert tokenize("a,,b") == ["a", "b"]
    assert tokenize("a,  ,b") == ["a", "b"]


def test_leading_and_trailing_delimiters_ignored():
    assert tokenize(",a,b,") == ["a", "b"]
    assert tokenize("   a   b   ") == ["a", "b"]


def test_empty_and_all_delimiters():
    assert tokenize("") == []
    assert tokenize(",, , ,") == []


def test_no_empty_strings_from_delimiters():
    # A delimiter-only mess (no quotes) must never leak "".
    for s in ["", ",", " ", ",,", " , ", "a,,b,,,c", ",,,a,,,"]:
        assert all(t != "" for t in tokenize(s)), f"empty token leaked from {s!r}"


def test_quoted_segment_is_one_token():
    assert tokenize('say "hello world" now') == ["say", "hello world", "now"]


def test_delimiters_inside_quotes_are_literal():
    assert tokenize('"a,b,c"') == ["a,b,c"]
    assert tokenize('x "a, b" y') == ["x", "a, b", "y"]


def test_quote_in_middle_of_token():
    # The quote chars are stripped; the quoted run joins the surrounding text.
    assert tokenize('a" b"c') == ["a bc"]


def test_explicit_empty_quoted_token_is_kept():
    # An explicitly quoted empty string is a deliberate (empty) token.
    assert tokenize('a "" b') == ["a", "", "b"]


def test_custom_delimiters():
    assert tokenize("a;b|c", delimiters=";|") == ["a", "b", "c"]
    assert tokenize("a;;|b", delimiters=";|") == ["a", "b"]
