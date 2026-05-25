from my_dict import *


def test_mbpp():
    assert my_dict({10})==False
    assert my_dict({11})==False
    assert my_dict({})==True
