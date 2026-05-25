"""Run-length encoding / decoding of strings.

Encoding format: each maximal run of a repeated character becomes the run
length (in decimal) followed by the character.

    encode("aaabbc")  -> "3a2b1c"
    encode("a")       -> "1a"
    encode("")        -> ""
    encode("aaaaaaaaaaaab") -> "12a1b"      (counts can be multi-digit)

decode is the exact inverse:

    decode("3a2b1c") -> "aaabbc"
    decode("12a1b")  -> "aaaaaaaaaaaab"

For any string s of letters, decode(encode(s)) == s.
"""


def encode(s: str) -> str:
    """Run-length encode a string as repeated '<count><char>' groups."""
    if not s:
        return ""
    out = []
    run_char = s[0]
    run_len = 1
    for ch in s[1:]:
        if ch == run_char:
            run_len += 1
        else:
            out.append(str(run_len) + run_char)
            run_char = ch
            run_len = 1
    # Flush the final run, which the loop above never emits on its own.
    out.append(str(run_len) + run_char)
    return "".join(out)


def decode(s: str) -> str:
    """Decode a run-length string produced by `encode` back to the original."""
    out = []
    count = 0
    for ch in s:
        if ch.isdigit():
            # Accumulate digits so multi-digit counts (e.g. "12") parse correctly.
            count = count * 10 + int(ch)
        else:
            out.append(ch * count)
            count = 0
    return "".join(out)
