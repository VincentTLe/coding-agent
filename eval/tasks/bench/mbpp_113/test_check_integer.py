from check_integer import *


def test_mbpp():
    assert check_integer("python")==False
    assert check_integer("1")==True
    assert check_integer("12345")==True
