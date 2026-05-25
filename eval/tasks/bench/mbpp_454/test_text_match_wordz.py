from text_match_wordz import *


def test_mbpp():
    assert text_match_wordz("pythonz.")==True
    assert text_match_wordz("xyz.")==True
    assert text_match_wordz("  lang  .")==False
