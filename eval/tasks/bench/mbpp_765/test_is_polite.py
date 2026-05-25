from is_polite import *


def test_mbpp():
    assert is_polite(7) == 11
    assert is_polite(4) == 7
    assert is_polite(9) == 13
