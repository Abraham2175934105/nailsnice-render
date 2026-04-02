from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class RolManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(nombre=name)

class Rol(models.Model):
    ADMIN = 'Administrador'
    CLIENTE = 'Cliente'
    EMPLEADO = 'Empleado'
    
    CHOICES_ROL = [
        (ADMIN, 'Administrador'),
        (CLIENTE, 'Cliente'),
        (EMPLEADO, 'Empleado'),
    ]
    
    nombre = models.CharField(
        max_length=50, 
        unique=True, 
        choices=CHOICES_ROL,
        default=CLIENTE
    )
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    objects = RolManager()
    
    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        usuario = self.model(email=email, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario
    
    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if 'id_rol' not in extra_fields and 'id_rol_id' not in extra_fields:
            # Usamos get_or_create para asegurar que no falle si la BD está limpia
            admin_rol, _ = Rol.objects.get_or_create(nombre=Rol.ADMIN)
            extra_fields['id_rol'] = admin_rol
            
        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('Suspendido', 'Suspendido'),
    ]
    
    email = models.EmailField(unique=True, max_length=50)
    nombre1 = models.CharField(max_length=50, blank=True, null=True)
    nombre2 = models.CharField(max_length=50, blank=True, null=True)
    apellido1 = models.CharField(max_length=50, blank=True, null=True)
    apellido2 = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=25, blank=True, null=True)
    estado_usuario = models.CharField(
        max_length=25,
        choices=ESTADO_CHOICES,
        default='Activo'
    )
    id_rol = models.ForeignKey(Rol, on_delete=models.PROTECT)
    
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    objects = UsuarioManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-creado_en']
    
    def __str__(self):
        nombre_completo = f"{self.nombre1 or ''} {self.apellido1 or ''}".strip()
        return nombre_completo or self.email


class Empleado(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='empleado')
    
    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
    
    def __str__(self):
        return f"Empleado: {self.usuario.email}"
