from text_starta_endb import *


def test_mbpp():
    assert text_starta_endb("aabbbb")
    assert not text_starta_endb("aabAbbbc")
    assert not text_starta_endb("accddbbjjj")
