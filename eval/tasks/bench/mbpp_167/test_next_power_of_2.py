from next_power_of_2 import *


def test_mbpp():
    assert next_power_of_2(0) == 1
    assert next_power_of_2(5) == 8
    assert next_power_of_2(17) == 32
