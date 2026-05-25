# he_050 — decode_shift

## Goal
def encode_shift(s: str):
    """
    returns encoded string by shifting every character by 5 in the alphabet.
    """
    return "".join([chr(((ord(ch) + 5 - ord("a")) % 26) + ord("a")) for ch in s])


def decode_shift(s: str):
    """
    takes as input string encoded with encode_shift function. Returns decoded string.
    """

Implement `decode_shift` in `decode_shift.py` so all tests pass.

## Category
strings

## Difficulty
medium

## Tests
hidden

## Source/License
HumanEval/50 via EvalPlus (HumanEval+). HumanEval: MIT; EvalPlus augmented tests: Apache-2.0.
