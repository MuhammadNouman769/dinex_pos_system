# DineX – Phase 1 backend (floors, settings, inventory)

Run tests: `python manage.py test tests`  (62 tests)

## Floors & restaurant settings
- `GET/POST /api/v1/orders/floors/`, `GET/PATCH/DELETE /api/v1/orders/floors/<id>/` (owner writes). Body: `{location, name, level}` (level: -1 basement, 0 ground, 1 first...).
- Tables take `floor` (`POST /orders/tables/ {location, floor, table_number, capacity}`).
- Location now has `tax_rate` (%), `service_charge_rate` (%), `inventory_policy` (ALLOW | WARN | BLOCK) – set with `PATCH /organizations/locations/<id>/`. Orders use these (no more fixed 10%); order has `service_charge`.

## Inventory (`/api/v1/inventory/`)
| Endpoint | Purpose |
|---|---|
| `ingredients/` , `ingredients/<id>/` | Ingredients (base unit G / ML / PCS). `is_prepared=true` = made in-house (patty, sauce). Owner writes |
| `stock/?location=&low=true` | Current stock per ingredient per location, value, low flag |
| `stock/movements/` GET/POST | Ledger. POST `{location, ingredient, movement_type: OPENING/PURCHASE/WASTAGE/ADJUSTMENT, quantity, unit, unit_cost, note}`. Owner or location MANAGER |
| `recipes/variant/<variant_id>/` GET/PUT/DELETE | Recipe of a menu item: `{output_quantity, lines:[{ingredient, quantity, unit}]}`; returns cost, profit, margin |
| `recipes/ingredient/<id>/` GET/PUT/DELETE | Recipe of a prepared ingredient (sub-recipe) |

Units accepted: g, kg, mg, ml, l, pcs, dozen (must match the ingredient's base unit). Stored in base units.

## How stock moves
- Order **CONFIRMED** (sent to kitchen) -> ingredients of every item are deducted (sub-recipes expanded).
- Items added/changed/removed after confirm -> only the **difference** moves.
- Order **CANCELLED** (or deleted) before PREPARING -> stock returned (`SALE_REVERSAL`). After cooking started the stock stays used.
- Policy per location: ALLOW (stock may go negative), WARN (response has `stock_warnings`), BLOCK (400, nothing changes).
- Every change is an immutable `StockMovement` row; prepared items hold no stock, their raw ingredients do.
