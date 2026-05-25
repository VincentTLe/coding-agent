from int_to_mini_roman import int_to_mini_roman


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
    inputs = [[19], [152], [251], [426], [500], [1], [4], [43], [90], [94], [532], [900], [994], [1000], [111], [888], [2], [10], [39], [100], [399], [871], [3], [5], [37], [870], [38], [889], [400], [872], [110], [6], [8], [7], [101], [109], [40], [36], [41], [35], [102], [34], [112], [113], [114], [9], [873], [874], [33], [891], [103], [42], [108], [868], [11], [869], [99], [22], [51], [887], [52], [890], [63], [12], [62], [55], [54], [14], [21], [45], [107], [13], [20], [398], [106], [98], [53], [23], [115], [105], [44], [56], [32], [104], [97], [57], [892], [31], [397], [886], [875], [64], [30], [26], [50], [96], [91], [46], [867], [885], [866], [18], [89], [88], [883], [15], [884], [29], [276], [388], [877], [935], [999], [864], [923], [603], [843], [936], [934], [865], [878], [937], [389], [933], [876], [95], [932], [998], [924], [997], [938], [386], [925], [385], [922], [387], [602], [842], [921], [275], [863], [840], [277], [931], [930], [844], [274], [927], [384], [928], [845], [841], [27], [996], [926], [28], [604], [279], [601], [278], [273], [929], [272], [280], [281], [600], [271], [605], [93], [879], [24], [995], [383], [25], [839], [382], [606], [390], [599], [598], [939], [48], [391], [78], [392], [992], [79], [76], [71], [862], [77], [861], [75], [80], [993], [70], [72], [61], [282], [81], [69], [73], [859], [74], [846], [393], [860], [920], [847], [858], [49], [82]]
    results = ['xix', 'clii', 'ccli', 'cdxxvi', 'd', 'i', 'iv', 'xliii', 'xc', 'xciv', 'dxxxii', 'cm', 'cmxciv', 'm', 'cxi', 'dccclxxxviii', 'ii', 'x', 'xxxix', 'c', 'cccxcix', 'dccclxxi', 'iii', 'v', 'xxxvii', 'dccclxx', 'xxxviii', 'dccclxxxix', 'cd', 'dccclxxii', 'cx', 'vi', 'viii', 'vii', 'ci', 'cix', 'xl', 'xxxvi', 'xli', 'xxxv', 'cii', 'xxxiv', 'cxii', 'cxiii', 'cxiv', 'ix', 'dccclxxiii', 'dccclxxiv', 'xxxiii', 'dcccxci', 'ciii', 'xlii', 'cviii', 'dccclxviii', 'xi', 'dccclxix', 'xcix', 'xxii', 'li', 'dccclxxxvii', 'lii', 'dcccxc', 'lxiii', 'xii', 'lxii', 'lv', 'liv', 'xiv', 'xxi', 'xlv', 'cvii', 'xiii', 'xx', 'cccxcviii', 'cvi', 'xcviii', 'liii', 'xxiii', 'cxv', 'cv', 'xliv', 'lvi', 'xxxii', 'civ', 'xcvii', 'lvii', 'dcccxcii', 'xxxi', 'cccxcvii', 'dccclxxxvi', 'dccclxxv', 'lxiv', 'xxx', 'xxvi', 'l', 'xcvi', 'xci', 'xlvi', 'dccclxvii', 'dccclxxxv', 'dccclxvi', 'xviii', 'lxxxix', 'lxxxviii', 'dccclxxxiii', 'xv', 'dccclxxxiv', 'xxix', 'cclxxvi', 'ccclxxxviii', 'dccclxxvii', 'cmxxxv', 'cmxcix', 'dccclxiv', 'cmxxiii', 'dciii', 'dcccxliii', 'cmxxxvi', 'cmxxxiv', 'dccclxv', 'dccclxxviii', 'cmxxxvii', 'ccclxxxix', 'cmxxxiii', 'dccclxxvi', 'xcv', 'cmxxxii', 'cmxcviii', 'cmxxiv', 'cmxcvii', 'cmxxxviii', 'ccclxxxvi', 'cmxxv', 'ccclxxxv', 'cmxxii', 'ccclxxxvii', 'dcii', 'dcccxlii', 'cmxxi', 'cclxxv', 'dccclxiii', 'dcccxl', 'cclxxvii', 'cmxxxi', 'cmxxx', 'dcccxliv', 'cclxxiv', 'cmxxvii', 'ccclxxxiv', 'cmxxviii', 'dcccxlv', 'dcccxli', 'xxvii', 'cmxcvi', 'cmxxvi', 'xxviii', 'dciv', 'cclxxix', 'dci', 'cclxxviii', 'cclxxiii', 'cmxxix', 'cclxxii', 'cclxxx', 'cclxxxi', 'dc', 'cclxxi', 'dcv', 'xciii', 'dccclxxix', 'xxiv', 'cmxcv', 'ccclxxxiii', 'xxv', 'dcccxxxix', 'ccclxxxii', 'dcvi', 'cccxc', 'dxcix', 'dxcviii', 'cmxxxix', 'xlviii', 'cccxci', 'lxxviii', 'cccxcii', 'cmxcii', 'lxxix', 'lxxvi', 'lxxi', 'dccclxii', 'lxxvii', 'dccclxi', 'lxxv', 'lxxx', 'cmxciii', 'lxx', 'lxxii', 'lxi', 'cclxxxii', 'lxxxi', 'lxix', 'lxxiii', 'dccclix', 'lxxiv', 'dcccxlvi', 'cccxciii', 'dccclx', 'cmxx', 'dcccxlvii', 'dccclviii', 'xlix', 'lxxxii']
    for i, (inp, exp) in enumerate(zip(inputs, results)):
        assertion(candidate(*inp), exp, 0)


def test_humaneval_plus():
    check(int_to_mini_roman)
