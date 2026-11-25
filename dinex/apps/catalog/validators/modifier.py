from rest_framework.exceptions import ValidationError


def validate_modifier_selection_rules(
    min_selections,
    max_selections,
    is_required,
):

    if max_selections < min_selections:
        raise ValidationError(
            {
                "max_selections": (
                    "Maximum selections cannot be "
                    "less than minimum selections."
                )
            }
        )

    if is_required and min_selections < 1:
        raise ValidationError(
            {
                "min_selections": (
                    "Required modifier groups must "
                    "have at least one selection."
                )
            }
        )