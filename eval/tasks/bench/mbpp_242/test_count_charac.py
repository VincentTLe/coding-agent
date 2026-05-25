from count_charac import *


def test_mbpp():
    assert count_charac("python programming")==18
    assert count_charac("language")==8
    assert count_charac("words")==5
