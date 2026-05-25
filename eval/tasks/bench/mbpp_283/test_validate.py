from validate import *


def test_mbpp():
    assert validate(1234) == True
    assert validate(51241) == False
    assert validate(321) == True
