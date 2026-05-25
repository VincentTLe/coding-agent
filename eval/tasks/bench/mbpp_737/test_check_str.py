from check_str import *


def test_mbpp():
    assert check_str("annie")
    assert not check_str("dawood")
    assert check_str("Else")
