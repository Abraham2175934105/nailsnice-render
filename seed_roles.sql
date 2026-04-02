-- Insertar Roles en usuarios_rol
INSERT INTO usuarios_rol (nombre, descripcion, creado_en, actualizado_en) VALUES
('Administrador', 'Administrador del sistema', NOW(), NOW()),
('Cliente', 'Cliente de la tienda', NOW(), NOW()),
('Empleado', 'Empleado de la tienda', NOW(), NOW());
