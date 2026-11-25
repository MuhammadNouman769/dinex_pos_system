"""Dish options (extra cheese, size of drink, spice level…): which groups a dish has, and picking from them."""
from decimal import Decimal

from rest_framework.exceptions import ValidationError


def effective_groups(product):
    """Active option groups attached to the dish, with per-dish overrides applied."""
    out = []
    links = product.modifier_group_links.filter(is_deleted=False, modifier_group__is_active=True, modifier_group__is_deleted=False).select_related("modifier_group").order_by("display_order", "id")
    for link in links:
        g = link.modifier_group
        mn = link.min_selections_override if link.min_selections_override is not None else g.min_selections
        mx = link.max_selections_override if link.max_selections_override is not None else g.max_selections
        required = link.is_required_override if link.is_required_override is not None else g.is_required
        if required and mn < 1:
            mn = 1
        out.append({
            "id": g.id, "link_id": link.id, "name": g.name, "min": mn, "max": mx, "required": bool(required),
            "options": [{"id": o.id, "name": o.name, "price": str(o.price_adjustment)}
                        for o in g.options.filter(is_active=True, is_deleted=False).order_by("position", "name")],
        })
    return out


def resolve(product, option_ids):
    """Validate the chosen option ids for this dish. Returns (snapshot list, total price adjustment)."""
    ids = list(option_ids or [])
    if len(ids) != len(set(ids)):
        raise ValidationError({"items": "The same option was chosen twice."})
    groups = effective_groups(product)
    by_option = {o["id"]: (g, o) for g in groups for o in g["options"]}
    chosen = {}
    for oid in ids:
        if oid not in by_option:
            raise ValidationError({"items": f"An option is not available for {product.name}."})
        g, o = by_option[oid]
        chosen.setdefault(g["id"], []).append(o)
    snapshot, total = [], Decimal("0")
    for g in groups:
        picked = chosen.get(g["id"], [])
        if len(picked) < g["min"]:
            raise ValidationError({"items": f"{product.name}: choose {g['name']}."})
        if g["max"] and len(picked) > g["max"]:
            raise ValidationError({"items": f"{product.name}: {g['name']} allows at most {g['max']}."})
        for o in picked:
            price = Decimal(o["price"])
            total += price
            snapshot.append({"id": o["id"], "group": g["name"], "name": o["name"], "price": str(price)})
    return snapshot, total
