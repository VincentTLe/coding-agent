# debugging_rle — run-length encode/decode

## Goal
`rle.py` performs run-length encoding and decoding of strings. Each maximal run
of a repeated character is encoded as its decimal length followed by the
character:

    encode("aaabbc")        -> "3a2b1c"
    encode("a")             -> "1a"
    encode("")              -> ""
    encode("a" * 12 + "b")  -> "12a1b"     (counts may be multi-digit)

`decode` is the exact inverse, so `decode(encode(s)) == s` for any letter
string `s`:

    decode("3a2b1c") -> "aaabbc"
    decode("12a1b")  -> "aaaaaaaaaaaab"

The suite in `test_rle.py` is failing. Run pytest, localize the bug(s), and fix
`rle.py` so every test passes. Do not edit the tests.

## Category
debugging

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
