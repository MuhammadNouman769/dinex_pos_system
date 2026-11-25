from django.contrib.auth.password_validation import (
    validate_password,
)

""" ======================= User Password Validator ======================= """

def validate_user_password(password):
    validate_password(password)
    return password