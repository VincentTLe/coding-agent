from is_not_prime import *


def test_mbpp():
    assert is_not_prime(2) == False
    assert is_not_prime(10) == True
    assert is_not_prime(35) == True
    assert is_not_prime(37) == False
