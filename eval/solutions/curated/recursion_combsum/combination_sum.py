def combination_sum(candidates, target):
    """All unique non-decreasing combinations of candidates summing to target."""
    if isinstance(target, bool) or not isinstance(target, int):
        raise ValueError("target must be an int")
    for c in candidates:
        if isinstance(c, bool) or not isinstance(c, int) or c <= 0:
            raise ValueError("candidates must be positive ints")

    uniq = sorted(set(candidates))
    results = []
    current = []

    def backtrack(start, remaining):
        if remaining == 0:
            results.append(list(current))
            return
        for i in range(start, len(uniq)):
            c = uniq[i]
            if c > remaining:
                break  # uniq is sorted; no larger candidate can fit either
            current.append(c)
            backtrack(i, remaining - c)  # i, not i+1: reuse allowed
            current.pop()

    if target < 0:
        return []
    backtrack(0, target)
    results.sort()
    return results
