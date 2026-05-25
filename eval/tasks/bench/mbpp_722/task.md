# mbpp_722 — filter_data

## Goal
The input is given as - a dictionary with a student name as a key and a tuple of float (student_height, student_weight) as a value, - minimal height, - minimal weight. Write a function to filter students that have height and weight above the minimum.

Implement `filter_data` in `filter_data.py` so the tests pass. Example checks:
assert filter_data({'Cierra Vega': (6.2, 70), 'Alden Cantrell': (5.9, 65), 'Kierra Gentry': (6.0, 68), 'Pierre Cox': (5.8, 66)},6.0,70)=={'Cierra Vega': (6.2, 70)}
assert filter_data({'Cierra Vega': (6.2, 70), 'Alden Cantrell': (5.9, 65), 'Kierra Gentry': (6.0, 68), 'Pierre Cox': (5.8, 66)},5.9,67)=={'Cierra Vega': (6.2, 70),'Kierra Gentry': (6.0, 68)}

## Category
algorithms

## Difficulty
easy

## Tests
hidden

## Source/License
MBPP sanitized task 722. MBPP: CC-BY-4.0.
