# he_038 — decode_cyclic

## Goal
def encode_cyclic(s: str):
    """
    returns encoded string by cycling groups of three characters.
    """
    # split string to groups. Each of length 3.
    groups = [s[(3 * i):min((3 * i + 3), len(s))] for i in range((len(s) + 2) // 3)]
    # cycle elements in each group. Unless group has fewer elements than 3.
    groups = [(group[1:] + group[0]) if len(group) == 3 else group for group in groups]
    return "".join(groups)


def decode_cyclic(s: str):
    """
    takes as input string encoded with encode_cyclic function. Returns decoded string.
    """

Implement `decode_cyclic` in `decode_cyclic.py` so all tests pass.

## Category
strings

## Difficulty
medium

## Tests
hidden

## Source/License
HumanEval/38 via EvalPlus (HumanEval+). HumanEval: MIT; EvalPlus augmented tests: Apache-2.0.
