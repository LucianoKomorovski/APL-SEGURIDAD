from django.db import migrations


def migrar_operadores(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    OperadorSistema = apps.get_model('accesos', 'OperadorSistema')
    CuentaSistema = apps.get_model('accesos', 'CuentaSistema')

    for operador in OperadorSistema.objects.all():
        usuario, creado = User.objects.get_or_create(
            username=operador.username,
            defaults={
                'first_name': operador.nombre,
                'last_name': operador.apellido,
                'email': operador.email,
                'password': operador.password_hash,
                'is_active': True,
            },
        )
        CuentaSistema.objects.get_or_create(
            persona_id=operador.pk,
            defaults={
                'usuario_id': usuario.pk,
                'rol': 'Operador',
                'activo': True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accesos', '0007_cuentas_sistema'),
    ]

    operations = [
        migrations.RunPython(migrar_operadores, migrations.RunPython.noop),
    ]
