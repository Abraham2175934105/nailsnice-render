from django.core.management.base import BaseCommand
from usuarios.models import Usuario, UsuarioRol, RolAcceso, Empleado
from clientes.models import Cliente


class Command(BaseCommand):
    help = 'Create missing Empleado and Cliente profile rows for users with corresponding roles.'

    def handle(self, *args, **options):
        created = {'empleado': 0, 'cliente': 0}

        try:
            rol_empleado = RolAcceso.objects.filter(codigo__iexact='EMPLEADO').first()
            rol_cliente = RolAcceso.objects.filter(codigo__iexact='CLIENTE').first()

            # Create Empleado profiles
            if rol_empleado:
                usuarios_emp = Usuario.objects.filter(roles_asignados__id_rol=rol_empleado).distinct()
                for u in usuarios_emp:
                    if not hasattr(u, 'empleado'):
                        codigo = f'EMP{getattr(u, "id_usuario", u.pk)}'
                        Empleado.objects.create(usuario=u, codigo_empleado=codigo)
                        created['empleado'] += 1

            # Create Cliente profiles
            if rol_cliente:
                usuarios_cli = Usuario.objects.filter(roles_asignados__id_rol=rol_cliente).distinct()
                for u in usuarios_cli:
                    if not hasattr(u, 'perfil_cliente'):
                        Cliente.objects.create(usuario=u)
                        created['cliente'] += 1

            self.stdout.write(self.style.SUCCESS(f"Created profiles: {created}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error creating profiles: {e}"))
*** End Patch