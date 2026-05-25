from starts_one_ends import starts_one_ends
import numpy as np

def is_floats(x) -> bool:
    # check if it is float; List[float]; Tuple[float]
    if isinstance(x, float):
        return True
    if isinstance(x, (list, tuple)):
        return all(isinstance(i, float) for i in x)
    if isinstance(x, np.ndarray):
        return x.dtype == np.float64 or x.dtype == np.float32
    return False


def assertion(out, exp, atol):
    exact_match = out == exp

    if atol == 0 and is_floats(exp):
        atol = 1e-6
    if not exact_match and atol != 0:
        np.testing.assert_allclose(out, exp, atol=atol)
    else:
        assert exact_match


def ref_func(n):


    if n == 1: return 1
    return 18 * 10 ** (n - 2)



def check(candidate):
    inputs = [[1], [2], [3], [4], [5], [6], [10], [12], [15], [20], [30], [8], [25], [100], [500], [29], [14], [26], [19], [13], [9], [101], [28], [21], [24], [7], [102], [99], [16], [501], [17], [22], [98], [11], [499], [1000], [1234], [9876], [31415], [1000000], [99999], [9877], [9878], [1235], [1001], [9879], [9880], [999999], [9881], [31414], [78], [999998], [999], [1002], [100000], [9882], [1233], [80], [999997], [1236], [1237], [1232], [79], [90], [31416], [31413], [31412], [31411], [1003], [999996], [68], [69], [1004], [97], [23], [9883], [89], [31417], [1231], [67], [100001], [50], [94], [82], [53], [52], [51], [9874], [31418], [77], [54], [9875], [76], [9873], [1000001], [96], [49], [1000002], [75], [998], [35], [39], [48], [34], [70], [38], [95], [997], [47]]
    for i, inp in enumerate(inputs):
        assertion(candidate(*inp), ref_func(*inp), 0)


def test_humaneval_plus():
    check(starts_one_ends)
