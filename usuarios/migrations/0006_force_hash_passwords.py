from django.db import migrations


def hash_placeholder_passwords(apps, schema_editor):
    """Force-hash placeholder/plaintext passwords in `hash_contrasena`.

    Targets rows where the `password` field is exactly '!' or empty/null, or
    where the value does not look like a Django hashed value (missing '$').
    Uses the User model's `set_password` to ensure the hash is written to the
    DB column mapped to the `password` field (db_column='hash_contrasena').
    """
    from django.contrib.auth.hashers import make_password

    Usuario = apps.get_model('usuarios', 'Usuario')

    placeholders = ['!', '', None]
    qs = Usuario.objects.all()
    # filter in Python to avoid ORM complexities across DB backends
    filtered = [u for u in qs if (u.password in placeholders) or ('$' not in (u.password or ''))]
    if not filtered:
        return

    for u in filtered:
        u.set_password('12345678Ns.')
        u.save(update_fields=['password'])


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_codigorecuperacion_and_more'),
    ]

    operations = [
        migrations.RunPython(hash_placeholder_passwords, reverse_code=migrations.RunPython.noop),
    ]
