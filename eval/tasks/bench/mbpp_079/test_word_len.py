from word_len import *


def test_mbpp():
    assert word_len("Hadoop") == False
    assert word_len("great") == True
    assert word_len("structure") == True
