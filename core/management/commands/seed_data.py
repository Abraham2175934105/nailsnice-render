from django.core.management.base import BaseCommand
from django.db import transaction
from usuarios.models import RolAcceso, Usuario, UsuarioRol

class Command(BaseCommand):
    help = 'Carga datos iniciales (Roles y Superusuario)'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🌱 Iniciando seed de datos...'))
        
        # 1. Crear Roles
        self.stdout.write('Creando Roles...')
        roles_data = [
            {'nombre': 'Administrador', 'descripcion': 'Administrador del sistema'},
            {'nombre': 'Cliente', 'descripcion': 'Cliente de la tienda'},
            {'nombre': 'Empleado', 'descripcion': 'Empleado de la tienda'},
        ]
        
        for rol_data in roles_data:
            # Creamos el código basado en el nombre
            codigo = rol_data['nombre'].upper()
            rol, created = RolAcceso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': rol_data['nombre'],
                    'descripcion': rol_data['descripcion']
                }
            )
            if created:
                self.stdout.write(f"  ✓ Rol '{rol.nombre}' creado")
            else:
                self.stdout.write(f"  - Rol '{rol.nombre}' ya existe")
        
        # 2. Crear Superusuario
        self.stdout.write('\nCreando Superusuario...')
        admin_rol = RolAcceso.objects.get(codigo='ADMINISTRADOR')
        
        # Usamos update_or_create sobre el correo
        admin, created = Usuario.objects.update_or_create(
            correo='admin@Profesional Beauty.com',
            defaults={
                'nombre': 'Admin',
                'apellido': 'Profesional Beauty',
                'estado': 'ACTIVO',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created:
            admin.set_password('Admin123!')
            admin.save()
            # Asignamos el rol en la tabla intermedia
            UsuarioRol.objects.get_or_create(id_usuario=admin, id_rol=admin_rol)
            
            self.stdout.write(self.style.SUCCESS("  ✓ Superusuario creado y rol asignado"))
            self.stdout.write(f"    Email: admin@Profesional Beauty.com")
            self.stdout.write(f"    Password: Admin123!")
        else:
            self.stdout.write("  - Superusuario ya existe")
        
        self.stdout.write(self.style.SUCCESS('\n✓ Seed de datos completado!'))