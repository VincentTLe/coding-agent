from dif_Square import *


def test_mbpp():
    assert dif_Square(5) == True
    assert dif_Square(10) == False
    assert dif_Square(15) == True
