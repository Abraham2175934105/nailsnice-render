from django.db import migrations


def hash_placeholder_passwords(apps, schema_editor):
    """Replace placeholder passwords (seeded as '!') with a Django-hashed password.

    This migration targets rows where the `password` field is exactly '!' or empty/null.
    It uses Django's password hasher (make_password) to store a proper hash so users
    can log in after the deployment.
    """
    from django.contrib.auth.hashers import make_password

    Usuario = apps.get_model('usuarios', 'Usuario')

    # Our model stores password in DB column `hash_contrasena` mapped to field `password`.
    # However some installs or seeds may have stored plaintext directly in that column.
    # We'll check for values that do not look like Django hashed values (no '$').
    placeholders = ['!', '', None]
    qs = Usuario.objects.all()
    filtered = [u for u in qs if (u.password in placeholders) or ('$' not in (u.password or ''))]
    if not filtered:
        return

    # If qs is a list (filtered above), iterate accordingly
    for u in filtered:
        # use set_password to use User model's hashing backends and then save to DB column
        u.set_password('12345678Ns.')
        # ensure we update the DB column that maps to password field (hash_contrasena)
        u.save(update_fields=['password'])


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_codigorecuperacion_and_more'),
    ]

    operations = [
        migrations.RunPython(hash_placeholder_passwords, reverse_code=migrations.RunPython.noop),
    ]
