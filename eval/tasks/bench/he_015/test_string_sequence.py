from string_sequence import string_sequence
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


def ref_func(n: int) -> str:


    return " ".join(map(str, range(n + 1)))



def check(candidate):
    inputs = [[0], [3], [10], [1], [100], [500], [2], [99], [1000], [10000], [15], [20], [50000], [49999], [101], [50001], [102], [49998], [1001], [18], [37], [36], [501], [84], [16], [10001], [65], [19], [66], [499], [83], [21], [98], [97], [17], [82], [22], [999], [67], [998], [50002], [9999], [75], [38], [498], [502], [96], [23], [50003], [9998], [76], [14], [29], [49997], [31], [85], [9997], [77], [503], [103], [13], [30], [86], [997], [1002], [35], [1003], [63], [39], [12], [68], [24], [1004], [4], [95], [78], [5], [25], [28], [50004], [104], [40], [9996], [64], [74], [10002], [94], [41], [105], [32], [73], [81], [26], [72], [6], [996], [42], [93], [79], [1000000], [1000001], [1000002], [999999], [1000003], [1000004], [34], [33], [27], [999998], [1000005], [999997], [87], [88], [89], [90], [1000006], [999996], [999995], [1000007], [7], [43], [44], [45], [999994], [999993], [1000008], [999992], [62], [61], [60], [59], [1000010], [999991], [1000009], [1000011]]
    for i, inp in enumerate(inputs):
        assertion(candidate(*inp), ref_func(*inp), 0)


def test_humaneval_plus():
    check(string_sequence)
