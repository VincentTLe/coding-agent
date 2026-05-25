from remove_all_spaces import *


def test_mbpp():
    assert remove_all_spaces('python  program')==('pythonprogram')
    assert remove_all_spaces('python   programming    language')==('pythonprogramminglanguage')
    assert remove_all_spaces('python                     program')==('pythonprogram')
    assert remove_all_spaces('   python                     program')=='pythonprogram'
