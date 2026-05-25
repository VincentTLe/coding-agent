from check_distinct import *


def test_mbpp():
    assert check_distinct((1, 4, 5, 6, 1, 4)) == False
    assert check_distinct((1, 4, 5, 6)) == True
    assert check_distinct((2, 3, 4, 5, 6)) == True
