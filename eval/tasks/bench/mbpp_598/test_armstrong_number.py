from armstrong_number import *


def test_mbpp():
    assert armstrong_number(153)==True
    assert armstrong_number(259)==False
    assert armstrong_number(4458)==False
