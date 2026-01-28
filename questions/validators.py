from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityPasswordValidator:
    """
    Validate that the password contains at least:
    - One uppercase letter
    - One lowercase letter
    - One digit
    - One special character
    """
    
    def __init__(self, min_uppercase=1, min_lowercase=1, min_digits=1, min_special=1):
        self.min_uppercase = min_uppercase
        self.min_lowercase = min_lowercase
        self.min_digits = min_digits
        self.min_special = min_special
    
    def validate(self, password, user=None):
        if not any(c.isupper() for c in password):
            raise ValidationError(
                _("This password must contain at least %(min)d uppercase letter."),
                code='password_no_uppercase',
                params={'min': self.min_uppercase},
            )
        
        if not any(c.islower() for c in password):
            raise ValidationError(
                _("This password must contain at least %(min)d lowercase letter."),
                code='password_no_lowercase',
                params={'min': self.min_lowercase},
            )
        
        if not any(c.isdigit() for c in password):
            raise ValidationError(
                _("This password must contain at least %(min)d digit."),
                code='password_no_digit',
                params={'min': self.min_digits},
            )
        
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            raise ValidationError(
                _("This password must contain at least %(min)d special character (!@#$%%^&*()_+-=[]{}|;:,.<>?)."),
                code='password_no_special',
                params={'min': self.min_special},
            )
    
    def get_help_text(self):
        return _(
            "Your password must contain at least one uppercase letter, "
            "one lowercase letter, one digit, and one special character."
        )
