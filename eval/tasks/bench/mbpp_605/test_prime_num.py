from prime_num import *


def test_mbpp():
    assert prime_num(13)==True
    assert prime_num(7)==True
    assert prime_num(-1010)==False
