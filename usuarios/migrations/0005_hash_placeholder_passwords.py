from django.db import migrations


def hash_placeholder_passwords(apps, schema_editor):
    """Replace placeholder passwords (seeded as '!') with a Django-hashed password.

    This migration targets rows where the `password` field is exactly '!' or empty/null.
    It uses Django's password hasher (make_password) to store a proper hash so users
    can log in after the deployment.
    """
    from django.contrib.auth.hashers import make_password

    Usuario = apps.get_model('usuarios', 'Usuario')

    placeholders = ['!', '', None]
    qs = Usuario.objects.filter(password__in=placeholders)
    if not qs.exists():
        return

    for u in qs:
        u.password = make_password('12345678Ns.')
        u.save(update_fields=['password'])


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_codigorecuperacion_and_more'),
    ]

    operations = [
        migrations.RunPython(hash_placeholder_passwords, reverse_code=migrations.RunPython.noop),
    ]
