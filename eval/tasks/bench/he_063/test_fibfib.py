from fibfib import fibfib


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
    inputs = [[2], [1], [5], [8], [10], [12], [14], [20], [0], [15], [23], [21], [25], [13], [19], [57], [22], [24], [56], [18], [False], [True], [58], [11], [26], [60], [4], [59], [16], [27], [28], [3], [17], [61], [62], [29], [30], [31], [32], [48], [47], [46], [55], [49], [50], [51], [52], [53], [54], [33], [73], [34], [63], [45], [72], [98], [100], [97], [71], [43], [9], [35], [44], [99], [102]]
    results = [1, 0, 4, 24, 81, 274, 927, 35890, 0, 1705, 223317, 66012, 755476, 504, 19513, 222332455004452, 121415, 410744, 120879712950776, 10609, 0, 0, 408933139743937, 149, 1389537, 1383410902447554, 2, 752145307699165, 3136, 2555757, 4700770, 1, 5768, 2544489349890656, 4680045560037375, 8646064, 15902591, 29249425, 53798080, 922906855808, 501774317241, 272809183135, 65720971788709, 1697490356184, 3122171529233, 5742568741225, 10562230626642, 19426970897100, 35731770264967, 98950096, 3814116544533214284, 181997601, 8607945812375585, 148323355432, 2073693258389777176, 15762679542071167858843489, 53324762928098149064722658, 8569995677610263592944752, 1127444240280152749, 43844049029, 44, 334745777, 80641778674, 28992087708416717612934417, 180396380815100901214157639]
    for i, (inp, exp) in enumerate(zip(inputs, results)):
        assertion(candidate(*inp), exp, 0)


def test_humaneval_plus():
    check(fibfib)
