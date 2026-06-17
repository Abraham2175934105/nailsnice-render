import os
import sys
import django

# Agregar la ruta actual para que Django encuentre el módulo settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nailsnice.settings")
django.setup()

from usuarios.models import Usuario, RolAcceso, UsuarioRol, Empleado
from clientes.models import Cliente
from django.core.exceptions import ObjectDoesNotExist

def fix_users():
    print("Iniciando revisión de perfiles y roles de usuario...")
    
    admin_role, _ = RolAcceso.objects.get_or_create(codigo='ADMIN', defaults={'nombre': 'Administrador', 'es_sistema': True})
    empleado_role, _ = RolAcceso.objects.get_or_create(codigo='EMPLEADO', defaults={'nombre': 'Empleado', 'es_sistema': True})
    cliente_role, _ = RolAcceso.objects.get_or_create(codigo='CLIENTE', defaults={'nombre': 'Cliente', 'es_sistema': True})
    
    usuarios = Usuario.objects.all()
    for user in usuarios:
        # 1. Asignar rol si no tiene
        if not user.roles_asignados.exists():
            if user.is_superuser or user.is_staff:
                UsuarioRol.objects.create(usuario=user, rol=admin_role)
                print(f"✅ Rol ADMIN asignado a {user.correo}")
            else:
                UsuarioRol.objects.create(usuario=user, rol=cliente_role)
                print(f"✅ Rol CLIENTE asignado a {user.correo}")
        
        # 2. Verificar perfil Empleado para admins/empleados
        rol = user.roles_asignados.first()
        if rol and rol.id_rol.codigo in ['ADMIN', 'EMPLEADO']:
            try:
                user.empleado
            except ObjectDoesNotExist:
                Empleado.objects.create(
                    usuario=user,
                    codigo_empleado=f"EMP-{user.id_usuario}",
                    cargo="Administrador/Staff",
                    activo=True
                )
                print(f"✅ Perfil Empleado creado para {user.correo}")

        # 3. Verificar perfil Cliente
        if rol and rol.id_rol.codigo == 'CLIENTE' or user.is_superuser:
            try:
                user.cliente
            except ObjectDoesNotExist:
                Cliente.objects.create(
                    usuario=user,
                    puntos_fidelidad=0
                )
                print(f"✅ Perfil Cliente creado para {user.correo}")

    print("Revisión completada con éxito.")

if __name__ == "__main__":
    fix_users()
