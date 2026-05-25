def trap(heights):
    """Total trapped rain water via the two-pointer technique (O(n) time, O(1) space)."""
    if any(h < 0 for h in heights):
        raise ValueError("heights must be non-negative")
    n = len(heights)
    if n < 3:
        return 0
    left, right = 0, n - 1
    left_max, right_max = heights[left], heights[right]
    total = 0
    while left < right:
        if left_max <= right_max:
            left += 1
            if heights[left] > left_max:
                left_max = heights[left]
            else:
                total += left_max - heights[left]
        else:
            right -= 1
            if heights[right] > right_max:
                right_max = heights[right]
            else:
                total += right_max - heights[right]
    return total
