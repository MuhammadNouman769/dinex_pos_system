from rest_framework.exceptions import ValidationError


def validate_product_variant_price(
    base_price,
    cost_price,
):
    if base_price < 0:
        raise ValidationError(
            {
                "base_price": (
                    "Base price cannot be negative."
                )
            }
        )

    if cost_price < 0:
        raise ValidationError(
            {
                "cost_price": (
                    "Cost price cannot be negative."
                )
            }
        )


def validate_variant_belongs_to_product(
    variant,
    product,
):
    if variant.product_id != product.id:
        raise ValidationError(
            "Selected variant does not belong to this product."
        )