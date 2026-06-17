from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class RolAcceso(models.Model):
    ADMIN = 'Administrador'
    CLIENTE = 'Cliente'
    EMPLEADO = 'Empleado'

    id_rol = models.BigAutoField(primary_key=True, db_column='id_rol')
    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField(null=True, blank=True)
    es_sistema = models.BooleanField(default=False, db_column='es_sistema')

    class Meta:
        db_table = 'rol_acceso'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.nombre.upper().replace(' ', '_')
        super().save(*args, **kwargs)


class PermisoAcceso(models.Model):
    id_permiso = models.BigAutoField(primary_key=True, db_column='id_permiso')
    codigo = models.CharField(max_length=80, unique=True)
    modulo = models.CharField(max_length=50)
    accion = models.CharField(max_length=50)
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'permiso_acceso'
        managed = True
        ordering = ['modulo', 'accion']

    def __str__(self):
        return f"{self.modulo} - {self.accion} ({self.codigo})"


class UsuarioManager(BaseUserManager):
    def create_user(self, correo=None, password=None, email=None, **extra_fields):
        correo = correo or email
        if not correo:
            raise ValueError('El correo electrónico es obligatorio')
        correo = self.normalize_email(correo)

        rol = extra_fields.pop('id_rol', None)
        nombre1 = extra_fields.pop('nombre1', None)
        apellido1 = extra_fields.pop('apellido1', None)

        if nombre1 is not None:
            extra_fields.setdefault('nombre', nombre1)
        if apellido1 is not None:
            extra_fields.setdefault('apellido', apellido1)

        usuario = self.model(correo=correo, **extra_fields)
        usuario.set_password(password)
        if not usuario.estado:
            usuario.estado = 'ACTIVO'
        usuario.save(using=self._db)

        if rol is not None:
            UsuarioRol.objects.create(id_usuario=usuario, id_rol=rol)

        return usuario

    def create_superuser(self, correo=None, password=None, email=None, **extra_fields):
        correo = correo or email
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('estado', 'ACTIVO')
        return self.create_user(correo, password, **extra_fields)


class Usuario(AbstractBaseUser):
    id_usuario = models.BigAutoField(primary_key=True, db_column='id_usuario')
    correo = models.EmailField(max_length=180, unique=True, db_column='correo')
    password = models.CharField(max_length=255, db_column='hash_contrasena')
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    estado = models.CharField(max_length=20, default='ACTIVO', db_index=True)
    is_staff = models.BooleanField(default=False, db_column='es_staff')
    is_superuser = models.BooleanField(default=False, db_column='es_superusuario')
    is_active = models.BooleanField(default=True, db_column='es_activo')
    last_login = models.DateTimeField(null=True, blank=True, db_column='ultimo_login')
    creado_en = models.DateTimeField(auto_now_add=True, db_column='creado_en')
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'usuario'
        managed = True
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.correo})"

    @property
    def email(self):
        """Backward-compatible alias used across the codebase and templates."""
        return self.correo

    @property
    def id(self):
        """Alias for primary key to support code that expects `user.id`."""
        return self.id_usuario

    @property
    def nombre1(self):
        return self.nombre

    @nombre1.setter
    def nombre1(self, value):
        self.nombre = value

    @property
    def apellido1(self):
        return self.apellido

    @apellido1.setter
    def apellido1(self, value):
        self.apellido = value

    @property
    def id_rol(self):
        # Uso seguro de getattr para prevenir que Pylance se queje de relaciones perezosas
        roles_mgr = getattr(self, 'roles_asignados', None)
        vinculo = roles_mgr.first() if roles_mgr else None
        return vinculo.id_rol if vinculo else None

    @property
    def rol_principal(self):
        """Helper para la UI: Obtiene el primer rol asignado al usuario"""
        roles_mgr = getattr(self, 'roles_asignados', None)
        vinculo = roles_mgr.first() if roles_mgr else None
        return vinculo.id_rol if vinculo else None

    @property
    def rol_asignado(self):
        roles_mgr = getattr(self, 'roles_asignados', None)
        return roles_mgr.select_related('id_rol').first() if roles_mgr else None

    def has_perm(self, perm, obj=None):
        if self.is_superuser:
            return True
        return RolPermiso.objects.filter(
            id_rol__usuarios_rol__id_usuario=self.id_usuario,
            id_permiso__codigo=perm
        ).exists()

    def has_module_perms(self, app_label):
        if self.is_superuser:
            return True
        return RolPermiso.objects.filter(
            id_rol__usuarios_rol__id_usuario=self.id_usuario,
            id_permiso__modulo=app_label
        ).exists()


class UsuarioRolQuerySet(models.QuerySet):
    def _normalize_kwargs(self, kwargs):
        normalized = kwargs.copy()
        for key in list(normalized.keys()):
            if key == 'usuario':
                normalized['id_usuario'] = normalized.pop('usuario')
            elif key.startswith('usuario__'):
                normalized[f'id_usuario__{key.split("usuario__",1)[1]}'] = normalized.pop(key)
            if key == 'rol':
                normalized['id_rol'] = normalized.pop('rol')
            elif key.startswith('rol__'):
                normalized[f'id_rol__{key.split("rol__",1)[1]}'] = normalized.pop(key)
        return normalized

    def filter(self, *args, **kwargs):
        return super().filter(*args, **self._normalize_kwargs(kwargs))

    def exclude(self, *args, **kwargs):
        return super().exclude(*args, **self._normalize_kwargs(kwargs))

    def get(self, *args, **kwargs):
        return super().get(*args, **self._normalize_kwargs(kwargs))

    def create(self, **kwargs):
        return super().create(**self._normalize_kwargs(kwargs))

    def get_or_create(self, defaults=None, **kwargs):
       kwargs = self._normalize_kwargs(kwargs)
       return super().get_or_create(defaults=defaults, **kwargs)

    def update_or_create(self, defaults=None, create_defaults=None, **kwargs):
       kwargs = self._normalize_kwargs(kwargs)
       return super().update_or_create(defaults=defaults, **kwargs)


class UsuarioRolManager(models.Manager.from_queryset(UsuarioRolQuerySet)):
    pass


class UsuarioRol(models.Model):
    objects = UsuarioRolManager()
    id_usuario_rol = models.BigAutoField(primary_key=True, db_column='id_usuario_rol')
    id_usuario = models.ForeignKey(Usuario, db_column='id_usuario', on_delete=models.CASCADE, related_name='roles_asignados')
    id_rol = models.ForeignKey(RolAcceso, db_column='id_rol', on_delete=models.CASCADE, related_name='usuarios_rol')

    class Meta:
        db_table = 'usuario_rol'
        managed = True
        unique_together = (('id_usuario', 'id_rol'),)

    def __init__(self, *args, **kwargs):
        if 'usuario' in kwargs:
            kwargs['id_usuario'] = kwargs.pop('usuario')
        if 'rol' in kwargs:
            kwargs['id_rol'] = kwargs.pop('rol')
        super().__init__(*args, **kwargs)

    @property
    def usuario(self):
        return self.id_usuario

    @usuario.setter
    def usuario(self, value):
        self.id_usuario = value

    @property
    def rol(self):
        return self.id_rol

    @rol.setter
    def rol(self, value):
        self.id_rol = value

    def __str__(self):
        return f"{self.id_usuario.correo} -> {self.id_rol.nombre}"


class RolPermiso(models.Model):
    id_rol_permiso = models.BigAutoField(primary_key=True, db_column='id_rol_permiso')
    id_rol = models.ForeignKey(RolAcceso, db_column='id_rol', on_delete=models.CASCADE, related_name='permisos_asignados')
    id_permiso = models.ForeignKey(PermisoAcceso, db_column='id_permiso', on_delete=models.CASCADE, related_name='roles_con_permiso')

    class Meta:
        db_table = 'rol_permiso'
        managed = True
        unique_together = (('id_rol', 'id_permiso'),)

    def __str__(self):
        return f"{self.id_rol.nombre} -> {self.id_permiso.codigo}"


Rol = RolAcceso


class Empleado(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        primary_key=True,
        db_column='id_usuario',
        on_delete=models.CASCADE,
        related_name='empleado'
    )
    codigo_empleado = models.CharField(max_length=40, unique=True)
    fecha_contratacion = models.DateField(null=True, blank=True)
    cargo = models.CharField(max_length=80, null=True, blank=True)
    activo = models.BooleanField(default=True)
    notas = models.CharField(max_length=255, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='creado_en')
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'perfil_empleado'
        managed = True
        ordering = ['usuario']

    def __str__(self):
        return f"Empleado: {self.usuario.nombre} {self.usuario.apellido} ({self.codigo_empleado})"


class CodigoRecuperacion(models.Model):
    """Código temporal para recuperación de contraseña enviado por email.

    Campos:
    - id_codigo: PK
    - usuario: FK a `Usuario` (nullable si el correo no existe en la app)
    - correo: email objetivo (repetido para consultas rápidas)
    - codigo: 6 dígitos (string)
    - creado_en: timestamp
    - expira_en: timestamp
    - usado: booleano para marcar uso
    """
    id_codigo = models.BigAutoField(primary_key=True, db_column='id_codigo')
    usuario = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.CASCADE, db_column='id_usuario', related_name='codigos_recuperacion')
    correo = models.EmailField(max_length=180, db_column='correo_objetivo', db_index=True)
    codigo = models.CharField(max_length=6, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_column='creado_en')
    expira_en = models.DateTimeField(db_column='expira_en')
    usado = models.BooleanField(default=False)

    class Meta:
        db_table = 'codigo_recuperacion'
        managed = True
        indexes = [
            models.Index(fields=['correo', 'codigo']),
        ]

    def __str__(self):
        return f"Codigo {self.codigo} -> {self.correo} (usado={self.usado})"