from django.core.management.base import BaseCommand
from usuarios.models import Rol, Usuario

class Command(BaseCommand):
    help = 'Carga datos iniciales (Roles y Superusuario)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🌱 Iniciando seed de datos...'))
        
        # Crear Roles
        self.stdout.write('Creando Roles...')
        roles_data = [
            {'nombre': 'Administrador', 'descripcion': 'Administrador del sistema'},
            {'nombre': 'Cliente', 'descripcion': 'Cliente de la tienda'},
            {'nombre': 'Empleado', 'descripcion': 'Empleado de la tienda'},
        ]
        
        for rol_data in roles_data:
            rol, created = Rol.objects.get_or_create(
                nombre=rol_data['nombre'],
                defaults={'descripcion': rol_data['descripcion']}
            )
            if created:
                self.stdout.write(f"  ✓ Rol '{rol.nombre}' creado")
            else:
                self.stdout.write(f"  - Rol '{rol.nombre}' ya existe")
        
        # Crear Superusuario
        self.stdout.write('\nCreando Superusuario...')
        admin_rol, _ = Rol.objects.get_or_create(nombre='Administrador')
        admin_defaults = {
            'nombre1': 'Admin',
            'apellido1': 'NailsNice',
            'estado_usuario': 'Activo',
            'id_rol': admin_rol,
            'is_staff': True,
            'is_superuser': True,
        }
        
        # Usamos update_or_create por si el usuario existe pero perdió permisos
        admin, created = Usuario.objects.update_or_create(
            email='admin@nailsnice.com',
            defaults=admin_defaults
        )
        
        if created:
            admin.set_password('Admin123!')
            admin.save()
            self.stdout.write(self.style.SUCCESS("  ✓ Superusuario creado"))
            self.stdout.write(f"    Email: admin@nailsnice.com")
            self.stdout.write(f"    Password: Admin123!")
        else:
            self.stdout.write("  - Superusuario ya existe")
        
        self.stdout.write(self.style.SUCCESS('\n✓ Seed de datos completado!'))
        self.stdout.write('\nAcceso a admin:')
        self.stdout.write('  http://localhost:8000/admin/')
