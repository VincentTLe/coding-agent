# multi_file_orders — Order fulfilment & reservation service

## Goal
Implement the order-fulfilment functions in `orders.py` so all tests in
`test_orders.py` pass.

The inventory primitives are already written for you in `inventory.py`
(an `Item` with `on_hand`/`reserved`, a `Warehouse` with `reserve`/`release`,
a `normalize_sku` helper, and the `UnknownSKU`/`NotEnoughStock` exceptions).
You MUST read `inventory.py` to implement `orders.py` correctly — note that
"available" stock is `on_hand - reserved`, that SKUs are normalised (trimmed +
upper-cased) before use, and that the warehouse already raises the right
exceptions.

An order is a mapping `{sku: quantity}`. Caller SKUs are not normalised, so
different casings/whitespace of the same SKU must be merged.

Implement these functions (full specs are in the `orders.py` docstrings):

- `normalize_order(order)` — new dict with SKUs normalised and duplicates
  merged (quantities summed). Every quantity must be a positive `int` (reject
  `bool`/non-ints) or raise `ValueError`.
- `shortfalls(warehouse, order)` — `{sku: missing}` for lines that can't be
  met now; an unknown SKU is fully short; met lines are omitted.
- `can_fulfil(warehouse, order)` — True iff every line can be reserved now,
  without mutating the warehouse.
- `reserve_order(warehouse, order)` — reserve the whole order atomically: if
  any line falls short, reserve nothing and raise `NotEnoughStock`/`UnknownSKU`.
- `cancel_order(warehouse, order)` — release each line's reservation; unknown
  SKUs are ignored.

Example:

```python
w = Warehouse(); w.stock("A-1", 10); w.stock("B-2", 5)
normalize_order({" a-1 ": 2, "A-1": 3})   # {"A-1": 5}
reserve_order(w, {"a-1": 4})               # A-1 reserved=4, available=6
shortfalls(w, {"A-1": 12})                 # {"A-1": 6}
```

## Category
multi_file

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
