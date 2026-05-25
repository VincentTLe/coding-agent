def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def flatten(nested):
    """Recursively flatten an arbitrarily nested list of integers."""
    out = []

    def go(node):
        for item in node:
            if isinstance(item, list):
                go(item)
            elif _is_int(item):
                out.append(item)
            else:
                raise TypeError(f"leaf must be a non-bool int, got {type(item).__name__}")

    if not isinstance(nested, list):
        raise TypeError("top-level argument must be a list")
    go(nested)
    return out


def flatten_depth(nested, depth):
    """Flatten ``nested`` by at most ``depth`` levels."""
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
        raise ValueError("depth must be a non-negative int")
    if not isinstance(nested, list):
        raise TypeError("top-level argument must be a list")

    def go(node, remaining):
        out = []
        for item in node:
            if isinstance(item, list):
                if remaining == 0:
                    # Preserved nested; not inspected for validity.
                    out.append(item)
                else:
                    out.extend(go(item, remaining - 1))
            elif _is_int(item):
                out.append(item)
            else:
                raise TypeError(f"leaf must be a non-bool int, got {type(item).__name__}")
        return out

    return go(nested, depth)
