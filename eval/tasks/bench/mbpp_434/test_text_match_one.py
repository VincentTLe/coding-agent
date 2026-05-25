from text_match_one import *


def test_mbpp():
    assert text_match_one("ac")==False
    assert text_match_one("dc")==False
    assert text_match_one("abba")==True
