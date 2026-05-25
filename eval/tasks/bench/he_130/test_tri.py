from tri import tri
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


    if n == 0: return [1]
    if n == 1: return [1, 3]
    ans = [1, 3]
    for i in range(2, n + 1):
        if i % 2 == 0:
            ans.append(1 + i / 2)
        else:
            ans.append(ans[-1] + ans[-2] + 1 + (i + 1) / 2)
    return ans



def check(candidate):
    inputs = [[3], [4], [5], [6], [7], [8], [9], [20], [0], [1], [2], [10], [15], [25], [13], [12], [30], [100], [35], [50], [99], [29], [24], [51], [16], [14], [26], [17], [18], [23], [49], [34], [98], [11], [28], [36], [22], [101], [102], [33], [31], [27], [21], [97], [32], [52], [48], [53], [47], [19], [103], [88], [87], [89], [96], [95], [46], [45], [44], [94], [104], [85], [37], [86], [43], [105], [42], [84], [38], [39], [106], [83], [82], [93], [108], [81], [41], [64], [40], [90], [54], [65], [66], [91], [63], [107], [67], [92], [109], [80], [62], [61], [55], [75], [79], [68], [111], [110], [1000000], [74], [73], [1000001], [999999], [999997], [999998], [999996], [999995], [76], [77], [78], [71], [72], [1000002], [1000003], [1000004]]
    for i, inp in enumerate(inputs):
        assertion(candidate(*inp), ref_func(*inp), 0)


def test_humaneval_plus():
    check(tri)
