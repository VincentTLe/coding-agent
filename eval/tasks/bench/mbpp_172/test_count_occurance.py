from count_occurance import *


def test_mbpp():
    assert count_occurance("letstdlenstdporstd") == 3
    assert count_occurance("truststdsolensporsd") == 1
    assert count_occurance("makestdsostdworthit") == 2
    assert count_occurance("stds") == 1
    assert count_occurance("") == 0
