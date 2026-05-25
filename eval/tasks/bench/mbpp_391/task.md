# mbpp_391 — convert_list_dictionary

## Goal
Write a function to convert more than one list to nested dictionary.

Implement `convert_list_dictionary` in `convert_list_dictionary.py` so the tests pass. Example checks:
assert convert_list_dictionary(["S001", "S002", "S003", "S004"],["Adina Park", "Leyton Marsh", "Duncan Boyle", "Saim Richards"] ,[85, 98, 89, 92])==[{'S001': {'Adina Park': 85}}, {'S002': {'Leyton Marsh': 98}}, {'S003': {'Duncan Boyle': 89}}, {'S004': {'Saim Richards': 92}}]
assert convert_list_dictionary(["abc","def","ghi","jkl"],["python","program","language","programs"],[100,200,300,400])==[{'abc':{'python':100}},{'def':{'program':200}},{'ghi':{'language':300}},{'jkl':{'programs':400}}]

## Category
algorithms

## Difficulty
easy

## Tests
hidden

## Source/License
MBPP sanitized task 391. MBPP: CC-BY-4.0.
