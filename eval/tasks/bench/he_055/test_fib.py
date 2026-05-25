from fib import fib


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


def check(candidate):
    inputs = [[10], [1], [8], [11], [12], [0], [False], [True], [16], [2], [17], [15], [14], [63], [64], [13], [3], [71], [72], [70], [35], [62], [69], [36], [34], [61], [67], [4], [5], [66], [65], [74], [73], [75], [44], [28], [18], [6], [45], [68], [29], [7], [27], [86], [60]]
    results = [55, 1, 21, 89, 144, 0, 0, 1, 987, 1, 1597, 610, 377, 6557470319842, 10610209857723, 233, 2, 308061521170129, 498454011879264, 190392490709135, 9227465, 4052739537881, 117669030460994, 14930352, 5702887, 2504730781961, 44945570212853, 3, 5, 27777890035288, 17167680177565, 1304969544928657, 806515533049393, 2111485077978050, 701408733, 317811, 2584, 8, 1134903170, 72723460248141, 514229, 13, 196418, 420196140727489673, 1548008755920]
    for i, (inp, exp) in enumerate(zip(inputs, results)):
        assertion(candidate(*inp), exp, 0)


def test_humaneval_plus():
    check(fib)
