from reverse_words import *


def test_mbpp():
    assert reverse_words("python program")==("program python")
    assert reverse_words("java language")==("language java")
    assert reverse_words("indian man")==("man indian")
