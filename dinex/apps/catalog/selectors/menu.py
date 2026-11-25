from apps.catalog.models import Menu


def get_menus_for_organization(
    organization,
):
    return (
        Menu.objects
        .filter(
            organization=organization,
            is_deleted=False,
        )
        .prefetch_related(
            "schedules",
            "sections__items__product_variant__product",
            "location_assignments__location",
        )
        .order_by("name")
    )


def get_menu(
    menu_id,
    organization,
):
    return (
        Menu.objects
        .filter(
            id=menu_id,
            organization=organization,
            is_deleted=False,
        )
        .prefetch_related(
            "schedules",
            "sections__items__product_variant__product",
            "location_assignments__location",
        )
        .first()
    )