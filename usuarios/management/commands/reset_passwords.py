from django.core.management.base import BaseCommand
from django.db import transaction
from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Actualiza la contraseña de todos los usuarios a la proporcionada. Usar con precaución.'

    def add_arguments(self, parser):
        parser.add_argument('--password', '-p', type=str, default='12345678Ns.', help='Nueva contraseña para todos los usuarios')
        parser.add_argument('--dry-run', action='store_true', help='No realiza cambios; muestra cuántos usuarios serían afectados')
        parser.add_argument('--skip-superusers', action='store_true', help='No actualizar superusuarios')

    def handle(self, *args, **options):
        password = options['password']
        dry_run = options['dry_run']
        skip_superusers = options['skip_superusers']

        qs = Usuario.objects.all()
        if skip_superusers:
            qs = qs.filter(is_superuser=False)

        total = qs.count()
        self.stdout.write(f"Usuarios a procesar: {total}")

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run: no se aplicaron cambios'))
            return

        updated = 0
        with transaction.atomic():
            for u in qs.iterator():
                u.set_password(password)
                # `password` es el nombre del campo de modelo mapeado a `hash_contrasena` en BD
                u.save(update_fields=['password'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Contraseñas actualizadas: {updated}'))
