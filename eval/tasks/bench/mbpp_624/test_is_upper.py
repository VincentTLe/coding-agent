from is_upper import *


def test_mbpp():
    assert is_upper("person") =="PERSON"
    assert is_upper("final") == "FINAL"
    assert is_upper("Valid") == "VALID"
