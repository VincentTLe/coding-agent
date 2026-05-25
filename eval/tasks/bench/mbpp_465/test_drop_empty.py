from drop_empty import *


def test_mbpp():
    assert drop_empty({'c1': 'Red', 'c2': 'Green', 'c3':None})=={'c1': 'Red', 'c2': 'Green'}
    assert drop_empty({'c1': 'Red', 'c2': None, 'c3':None})=={'c1': 'Red'}
    assert drop_empty({'c1': None, 'c2': 'Green', 'c3':None})=={ 'c2': 'Green'}
