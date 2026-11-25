# Common App

The `common` app contains reusable components shared across the MN Kitchen POS backend.

It should contain only generic functionality and should not contain business-specific
models or logic.

## Files and Use Cases

### base_model.py
Reusable abstract Django models.

Used for:
- Common timestamps
- Soft delete
- UUID
- Ordering
- Slugs

Used by models in:
- restaurants
- accounts
- products
- customers
- orders
- kitchen
- inventory


### base_serializer.py
Base serializer for common serializer behavior.

Used by serializers across different apps.


### base_viewset.py
Reusable DRF ViewSet functionality.

Used by API ViewSets where common behavior is required.


### base_service.py
Base class/common structure for business services.

Complex business logic should be handled in service classes instead of views.


### constants.py
Stores reusable fixed values.

Examples:
- Pagination limits
- Order prefixes
- KOT prefixes
- Currency-related constants


### enums.py
Stores reusable choices and statuses.

Examples:
- Order status
- Payment status
- KOT status
- Table status
- Inventory movement type


### helpers.py
Small reusable helper functions.

Examples:
- Generate reference numbers
- Generate codes
- Format values
- Request-related helpers


### permissions.py
Reusable DRF permissions.

Examples:
- Admin
- Manager
- Cashier
- Waiter
- Kitchen staff


### responses.py
Provides consistent API success and error response formats.


### pagination.py
Provides standard API pagination.

Used for:
- Products
- Orders
- Customers
- Inventory
- Reports


### mixins.py
Reusable DRF mixins.

Used when the same behavior is required by multiple ViewSets.


### exceptions.py
Global DRF exception handling.

Provides a consistent error response format for API errors.


### validators.py
Reusable validation functions.

Used for:
- Prices
- Quantities
- Discounts
- Phone numbers
- Other common validations


### middleware.py
Reusable Django middleware.

Possible uses:
- Request logging
- Activity tracking
- Tenant/request context
- Other global request processing


## Important Rule

`common` should contain reusable functionality only.

Do NOT create POS business models inside `common`.

Business models belong to their respective apps.

Example:

- Restaurant → `restaurants`
- User/Staff → `accounts`
- Product/Category → `products`
- Customer → `customers`
- Table/Floor → `tables`
- Order/Payment → `orders`
- KOT/Kitchen → `kitchen`
- Stock/Purchase → `inventory`
- Reports → `reports`

## Model Usage

Most normal models:

`BaseModel`

Models requiring ordering:

`OrderedModel`

Models requiring URL slugs:

`SluggedModel`

Models requiring UUID:

`UUIDModel`

## Architecture

Models
→ Serializers
→ Services
→ Permissions
→ ViewSets
→ URLs
→ API

Common provides reusable components for these layers.