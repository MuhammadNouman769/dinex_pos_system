from apps.accounts.validators.user_validators import (
    validate_user_password,
)

""" ======================= User Password Serializer Validator ======================= """

def validate_password(self, value):
    validate_user_password(value)
    return value