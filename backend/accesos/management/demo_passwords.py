import os

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError


def demo_passwords():
    passwords = [os.getenv('APL_DEMO_OPERATOR_PASSWORD'), os.getenv('APL_DEMO_TECH_PASSWORD')]
    if settings.DEBUG and not any(passwords):
        return ('apl2026', 'apl2026')  # Solo compatibilidad con la demo local histórica.
    if not all(passwords):
        raise CommandError('Usá crear_demo_segura para establecer ambas contraseñas nuevas.')
    try:
        for password in passwords:
            validate_password(password)
            if password == 'apl2026':
                raise ValidationError('No se permite la contraseña de la demo local online.')
    except ValidationError as exc:
        raise CommandError('; '.join(exc.messages)) from exc
    return passwords
