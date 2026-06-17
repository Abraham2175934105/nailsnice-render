-- Seed data for Nails_Nice_py
-- Generated: 2026-06-17
-- IMPORTANT:
-- 1) This file inserts sample data with referential integrity for main tables.
-- 2) Passwords are set to unusable placeholders (!) — use Django management to set real passwords:
--    python manage.py shell
--    from django.contrib.auth.hashers import make_password
--    from usuarios.models import Usuario
--    u = Usuario.objects.get(correo='admin@nailsnice.test')
--    u.hash_contrasena = make_password('TuPasswordSeguro123!')
--    u.save()

BEGIN;

-- ------------------------------------------------------------------
-- Roles (rol_acceso)
-- ------------------------------------------------------------------
INSERT INTO rol_acceso (id_rol, codigo, nombre, descripcion, es_sistema)
VALUES
  (1, 'ADMIN', 'Administrador', 'Acceso total al sistema', true),
  (2, 'EMPLEADO', 'Empleado', 'Usuario con permisos operativos', true),
  (3, 'CLIENTE', 'Cliente', 'Rol para clientes', true),
  (4, 'GERENTE', 'Gerente', 'Responsable de sucursal', true),
  (5, 'SUPERVISOR', 'Supervisor', 'Supervisa operaciones', false),
  (6, 'RECEPCIONISTA', 'Recepcionista', 'Atiende reservas y caja', false),
  (7, 'TECNICO', 'Técnico', 'Realiza servicios técnicos', false),
  (8, 'VENDEDOR', 'Vendedor', 'Ventas y atención', false),
  (9, 'CONTADOR', 'Contador', 'Reportes financieros', false),
  (10, 'MARKETING', 'Marketing', 'Promociones y contenidos', false);

-- ------------------------------------------------------------------
-- Users (usuario)
-- id_usuario chosen explicitly for referential seeding
-- ------------------------------------------------------------------
INSERT INTO usuario (id_usuario, correo, hash_contrasena, nombre, apellido, telefono, estado, es_staff, es_superusuario, es_activo, ultimo_login, creado_en, actualizado_en)
VALUES
  (1000, 'admin@nailsnice.test', '!', 'Admin', 'Nails', '+571000000000', 'ACTIVO', true, true, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1001, 'juan.perez@nailsnice.test', '!', 'Juan', 'Pérez', '+573001234001', 'ACTIVO', true, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1002, 'maria.lopez@nailsnice.test', '!', 'María', 'López', '+573001234002', 'ACTIVO', true, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1003, 'andres.garcia@nailsnice.test', '!', 'Andrés', 'García', '+573001234003', 'ACTIVO', true, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1004, 'laura.martinez@nailsnice.test', '!', 'Laura', 'Martínez', '+573001234004', 'ACTIVO', true, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1005, 'pedro.romeo@nailsnice.test', '!', 'Pedro', 'Romero', '+573001234005', 'ACTIVO', true, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1006, 'empleado6@nailsnice.test', '!', 'Sergio', 'Ramos', '+573001234006', 'ACTIVO', true, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1007, 'empleado7@nailsnice.test', '!', 'Luisa', 'Cárdenas', '+573001234007', 'ACTIVO', true, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1008, 'empleado8@nailsnice.test', '!', 'Carlos', 'Estrada', '+573001234008', 'ACTIVO', true, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1009, 'empleado9@nailsnice.test', '!', 'Ana', 'Gómez', '+573001234009', 'ACTIVO', true, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  -- Clients (will be linked to perfil_cliente)
  (1010, 'cliente1@example.com', '!', 'Valentina', 'Sosa', '+57301234010', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1011, 'cliente2@example.com', '!', 'Miguel', 'Torres', '+57301234011', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1012, 'cliente3@example.com', '!', 'Catalina', 'Romero', '+57301234012', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1013, 'cliente4@example.com', '!', 'Diego', 'Fuentes', '+57301234013', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1014, 'cliente5@example.com', '!', 'Mariana', 'Ruiz', '+57301234014', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1015, 'cliente6@example.com', '!', 'Fernando', 'Arias', '+57301234015', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1016, 'cliente7@example.com', '!', 'Laura', 'Pérez', '+57301234016', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1017, 'cliente8@example.com', '!', 'Julián', 'Meza', '+57301234017', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1018, 'cliente9@example.com', '!', 'Sofia', 'López', '+57301234018', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1019, 'cliente10@example.com', '!', 'Andrés', 'Molina', '+57301234019', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  -- Additional regular users (creators / placeholders)
  (1020, 'content@nailsnice.test', '!', 'Contento', 'Medina', '+573001234020', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1021, 'ventas@nailsnice.test', '!', 'Vendedor', 'Perez', '+573001234021', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1022, 'soporte@nailsnice.test', '!', 'Soporte', 'Vega', '+573001234022', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1023, 'tester01@nailsnice.test', '!', 'Test', 'Uno', '+573001234023', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1024, 'tester02@nailsnice.test', '!', 'Test', 'Dos', '+573001234024', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1025, 'marketing@nailsnice.test', '!', 'Marketing', 'Rocha', '+573001234025', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1026, 'finanzas@nailsnice.test', '!', 'Finanzas', 'Ortega', '+573001234026', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1027, 'logistica@nailsnice.test', '!', 'Logistica', 'Salas', '+573001234027', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1028, 'gerencia@nailsnice.test', '!', 'Gerente', 'Lozano', '+573001234028', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1029, 'reportes@nailsnice.test', '!', 'Reportes', 'Cruz', '+573001234029', 'ACTIVO', false, false, true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- ------------------------------------------------------------------
-- User roles (usuario_rol) mapping
-- ------------------------------------------------------------------
INSERT INTO usuario_rol (id_usuario_rol, id_usuario, id_rol)
VALUES
  (1, 1000, 1), -- admin
  (2, 1001, 2),
  (3, 1002, 2),
  (4, 1003, 2),
  (5, 1004, 2),
  (6, 1005, 2),
  (7, 1006, 2),
  (8, 1007, 2),
  (9, 1008, 2),
  (10, 1009, 2),
  (11, 1010, 3),
  (12, 1011, 3),
  (13, 1012, 3),
  (14, 1013, 3),
  (15, 1014, 3),
  (16, 1015, 3),
  (17, 1016, 3),
  (18, 1017, 3),
  (19, 1018, 3),
  (20, 1019, 3),
  (21, 1028, 4),
  (22, 1026, 9),
  (23, 1025, 10);

-- ------------------------------------------------------------------
-- Clients (perfil_cliente)
-- ------------------------------------------------------------------
INSERT INTO perfil_cliente (id_usuario, fecha_nacimiento, acepta_fidelizacion, creado_en, actualizado_en)
VALUES
  (1010, '1995-04-12', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1011, '1988-11-03', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1012, '1992-07-21', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1013, '1990-02-15', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1014, '1985-09-30', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1015, '1997-12-01', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1016, '1999-06-05', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1017, '1994-08-19', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1018, '2000-01-25', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1019, '1996-03-11', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Addresses for clients (direccion_usuario)
INSERT INTO direccion_usuario (id_direccion, id_usuario, tipo_direccion, etiqueta, nombre_destinatario, linea1, linea2, ciudad, departamento, codigo_postal, codigo_pais, es_predeterminada_envio, es_predeterminada_factura, creado_en, actualizado_en)
VALUES
  (1, 1010, 'ENVIO', 'Casa', 'Valentina Sosa', 'Calle 10 #12-34', NULL, 'Bogotá', 'Cundinamarca', '110111', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (2, 1011, 'ENVIO', 'Trabajo', 'Miguel Torres', 'Av 15 #45-67', 'Oficina 201', 'Medellín', 'Antioquia', '050021', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (3, 1012, 'ENVIO', 'Casa', 'Catalina Romero', 'Cra 8 #22-10', NULL, 'Cali', 'Valle del Cauca', '760001', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (4, 1013, 'ENVIO', 'Casa', 'Diego Fuentes', 'Calle 25 #5-18', NULL, 'Barranquilla', 'Atlántico', '080001', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5, 1014, 'ENVIO', 'Casa', 'Mariana Ruiz', 'Av 30 #12-11', NULL, 'Bucaramanga', 'Santander', '680001', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6, 1015, 'ENVIO', 'Casa', 'Fernando Arias', 'Calle 2 #3-45', NULL, 'Pereira', 'Risaralda', '660001', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (7, 1016, 'ENVIO', 'Casa', 'Laura Pérez', 'Cra 16 #8-20', NULL, 'Manizales', 'Caldas', '170001', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (8, 1017, 'ENVIO', 'Casa', 'Julián Meza', 'Av 19 #5-50', NULL, 'Cúcuta', 'Norte de Santander', '540001', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (9, 1018, 'ENVIO', 'Casa', 'Sofia López', 'Calle 40 #7-80', NULL, 'Ibagué', 'Tolima', '730001', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (10, 1019, 'ENVIO', 'Casa', 'Andrés Molina', 'Cra 25 #2-10', NULL, 'Cartagena', 'Bolívar', '130001', 'CO', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- ------------------------------------------------------------------
-- Payment providers and types
-- ------------------------------------------------------------------
INSERT INTO proveedor_pago (id_proveedor, codigo, nombre, activo) VALUES
  (1, 'PAYU', 'PayU Latam', true),
  (2, 'STRIPE', 'Stripe', true),
  (3, 'PLACEHOLDER', 'Tarjeta Demo', true);

INSERT INTO tipo_metodo_pago (id_tipo_metodo, codigo, nombre, activo) VALUES
  (1, 'TARJETA', 'Tarjeta de crédito/débito', true),
  (2, 'EFECTIVO', 'Efectivo', true),
  (3, 'PSE', 'PSE/Transferencia', true);

-- Minimal payment tokens for clients
INSERT INTO metodo_pago_cliente (id_metodo_pago, id_usuario_cliente, id_tipo_metodo, id_proveedor, token, etiqueta_mascara, nombre_titular, ultimos4, mes_expiracion, anio_expiracion, es_predeterminado, estado, creado_en, actualizado_en)
VALUES
  (1, 1010, 1, 1, 'tok_visa_1010', 'Visa ****1010', 'Valentina Sosa', '1010', 12, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (2, 1011, 1, 2, 'tok_card_1111', 'MC ****1111', 'Miguel Torres', '1111', 11, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (3, 1012, 1, 3, 'tok_card_1212', 'Visa ****1212', 'Catalina Romero', '1212', 10, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (4, 1013, 1, 1, 'tok_card_1313', 'Visa ****1313', 'Diego Fuentes', '1313', 9, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5, 1014, 1, 2, 'tok_card_1414', 'MC ****1414', 'Mariana Ruiz', '1414', 8, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6, 1015, 1, 3, 'tok_card_1515', 'Visa ****1515', 'Fernando Arias', '1515', 7, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (7, 1016, 1, 1, 'tok_card_1616', 'Visa ****1616', 'Laura Pérez', '1616', 6, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (8, 1017, 1, 2, 'tok_card_1717', 'MC ****1717', 'Julián Meza', '1717', 5, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (9, 1018, 1, 3, 'tok_card_1818', 'Visa ****1818', 'Sofia López', '1818', 4, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (10, 1019, 1, 1, 'tok_card_1919', 'MC ****1919', 'Andrés Molina', '1919', 3, 2026, true, 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- ------------------------------------------------------------------
-- Catalog: Brands, Categories, Subcategories
-- ------------------------------------------------------------------
INSERT INTO marca_catalogo (id_marca, nombre, descripcion, activo, creado_en)
VALUES
  (1, 'NailArt Pro', 'Marca profesional de esmaltes y geles', true, CURRENT_TIMESTAMP),
  (2, 'GlamNails', 'Productos para manicure de alta duración', true, CURRENT_TIMESTAMP),
  (3, 'PedicurePlus', 'Especialistas en pedicure y cuidado', true, CURRENT_TIMESTAMP),
  (4, 'ColorLuxe', 'Esmaltes importados', true, CURRENT_TIMESTAMP),
  (5, 'StudioGlow', 'Productos de salón premium', true, CURRENT_TIMESTAMP),
  (6, 'NailDesigns', 'Accesorios y decoración', true, CURRENT_TIMESTAMP),
  (7, 'GelMaster', 'Geles y acrílicos profesionales', true, CURRENT_TIMESTAMP),
  (8, 'PureNails', 'Líneas naturales y veganas', true, CURRENT_TIMESTAMP),
  (9, 'SparkleCo', 'Brillos y efectos especiales', true, CURRENT_TIMESTAMP),
  (10, 'HydraCare', 'Cuidado y tratamientos', true, CURRENT_TIMESTAMP);

INSERT INTO categoria_catalogo (id_categoria, nombre, slug, descripcion, activo, creado_en)
VALUES
  (1, 'Manicure', 'manicure', 'Servicios y productos para manicure', true, CURRENT_TIMESTAMP),
  (2, 'Pedicure', 'pedicure', 'Servicios y productos para pedicure', true, CURRENT_TIMESTAMP),
  (3, 'Decoracion', 'decoracion-uñas', 'Decoraciones y arte para uñas', true, CURRENT_TIMESTAMP),
  (4, 'Tratamientos', 'tratamientos', 'Tratamientos de cuidado de uñas', true, CURRENT_TIMESTAMP),
  (5, 'Herramientas', 'herramientas', 'Herramientas de salón', true, CURRENT_TIMESTAMP),
  (6, 'Kits', 'kits', 'Kits y sets', true, CURRENT_TIMESTAMP),
  (7, 'Accesorios', 'accesorios', 'Accesorios decorativos', true, CURRENT_TIMESTAMP),
  (8, 'Geles', 'geles', 'Geles y acrílicos', true, CURRENT_TIMESTAMP),
  (9, 'Esmaltes', 'esmaltes', 'Esmaltes en diversos acabados', true, CURRENT_TIMESTAMP),
  (10, 'Cuidado', 'cuidado', 'Productos de cuidado y salud de uñas', true, CURRENT_TIMESTAMP);

INSERT INTO subcategoria_catalogo (id_subcategoria, id_categoria, nombre, slug, descripcion, activo, creado_en)
VALUES
  (1, 1, 'Manicure Clásico', 'manicure-clasico', 'Manicure tradicional', true, CURRENT_TIMESTAMP),
  (2, 1, 'Manicure Gel', 'manicure-gel', 'Manicure con gel', true, CURRENT_TIMESTAMP),
  (3, 1, 'Manicure Acrílico', 'manicure-acrilico', 'Uñas acrílicas', true, CURRENT_TIMESTAMP),
  (4, 2, 'Pedicure Spa', 'pedicure-spa', 'Pedicure con tratamiento', true, CURRENT_TIMESTAMP),
  (5, 3, 'Arte y Decoración', 'arte-decoracion', 'Stickers y decoraciones', true, CURRENT_TIMESTAMP),
  (6, 9, 'Esmaltes Mate', 'esmaltes-mate', 'Acabado mate', true, CURRENT_TIMESTAMP),
  (7, 9, 'Esmaltes Brillo', 'esmaltes-brillo', 'Acabado brillante', true, CURRENT_TIMESTAMP),
  (8, 8, 'Geles UV', 'geles-uv', 'Geles curables UV', true, CURRENT_TIMESTAMP),
  (9, 4, 'Tratamientos Fortalecedores', 'tratamientos-fortalecedores', 'Vitaminas y fortalecedores', true, CURRENT_TIMESTAMP),
  (10, 7, 'Accesorios Brillo', 'accesorios-brillo', 'Pedrería y brillos', true, CURRENT_TIMESTAMP);

-- ------------------------------------------------------------------
-- Products, variants and images (10 products with 1 variante each + images)
-- Use Unsplash image URLs for `ruta_almacenamiento`
-- ------------------------------------------------------------------
INSERT INTO producto (id_producto, id_subcategoria, id_marca, nombre, slug, descripcion_corta, descripcion_larga, descripcion_tecnica, estado, creado_por, creado_en, actualizado_en)
VALUES
  (5001, 1, 1, 'Manicure Clásico - Set', 'manicure-clasico-set', 'Set básico para manicure', 'Incluye lima, cortaúñas y esmalte base.', 'Ingredientes: alcohol, acetato', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5002, 2, 2, 'Gel Builder - Pink', 'gel-builder-pink', 'Gel constructor color rosa', 'Gel para construcción de uñas con acabado natural.', 'Uso profesional bajo lámpara UV/LED', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5003, 3, 3, 'Acrílico Premium White', 'acrilico-premium-white', 'Polvo acrílico color blanco', 'Polvo acrílico de alta cobertura.', 'Secado rápido', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5004, 5, 6, 'Stickers Flores', 'stickers-flores', 'Stickers decorativos para uñas', 'Set de stickers de flores variadas.', 'Aplicar después del esmalte base', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5005, 6, 4, 'Esmalte Mate - Negro', 'esmalte-mate-negro', 'Esmalte acabado mate', 'Acabado mate intenso en una capa.', 'Secado rápido, alta pigmentación', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5006, 7, 9, 'Esmalte Brillo - Rojo', 'esmalte-brillo-rojo', 'Esmalte brillante rojo vivo', 'Color rojo clásico con brillo.', 'Ingredientes: nitrocelulosa, solvente', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5007, 8, 7, 'Gel UV - Clear', 'gel-uv-clear', 'Gel transparente para sellado', 'Gel transparente de curado rápido.', 'Requiere lámpara UV/LED', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5008, 4, 3, 'Pedicure Spa - Sal', 'pedicure-spa-sal', 'Sales relajantes para pedicure', 'Sales aromáticas para baño de pies.', 'Contiene sales minerales', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5009, 9, 5, 'Tratamiento Fortalecedor', 'tratamiento-fortalecedor', 'Tratamiento para uñas frágiles', 'Sérum vitamínico fortalecedor.', 'Aplicar 2 veces por semana', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (5010, 10, 6, 'Pedrería Mix', 'pedreria-mix', 'Mix de pedrería para decoración', 'Pedrería y cristales variados para uñas.', 'Distintos tamaños y colores', 'ACTIVO', 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Variants
INSERT INTO variante_producto (id_variante, id_producto, sku, codigo_barras, nombre_variante, precio, costo, codigo_moneda, peso_gramos, activo, creado_en, actualizado_en)
VALUES
  (6001, 5001, 'SKUMAN-0001', NULL, 'Set Básico', 35000.00, 15000.00, 'COP', 120.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6002, 5002, 'SKUGEL-0002', NULL, 'Gel Pink 30ml', 45000.00, 22000.00, 'COP', 80.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6003, 5003, 'SKUACR-0003', NULL, 'Acrílico White 50g', 30000.00, 12000.00, 'COP', 60.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6004, 5004, 'SKUSTICK-0004', NULL, 'Stickers Flores', 12000.00, 3000.00, 'COP', 10.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6005, 5005, 'SKUESM-MAT-0005', NULL, 'Esmalte Mate 13ml', 18000.00, 6000.00, 'COP', 40.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6006, 5006, 'SKUESM-BR-0006', NULL, 'Esmalte Brillo 13ml', 18000.00, 6000.00, 'COP', 40.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6007, 5007, 'SKUGELC-0007', NULL, 'Gel Clear 30ml', 42000.00, 20000.00, 'COP', 80.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6008, 5008, 'SKUSPASAL-0008', NULL, 'Sal Spa 500g', 25000.00, 9000.00, 'COP', 600.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6009, 5009, 'SKUTRAT-0009', NULL, 'Sérum Fortalecedor 30ml', 38000.00, 14000.00, 'COP', 50.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (6010, 5010, 'SKUPEDR-0010', NULL, 'Mix Pedrería', 15000.00, 4000.00, 'COP', 30.00, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Product images (use high-quality Unsplash images about nails/manicure/pedicure)
INSERT INTO imagen_producto (id_imagen, id_producto, id_variante, ruta_almacenamiento, texto_alternativo, orden, es_principal, creado_en)
VALUES
  (7001, 5001, 6001, 'https://images.unsplash.com/photo-1519744792095-2f2205e87b6f', 'Manicure clásico - set básico', 0, true, CURRENT_TIMESTAMP),
  (7002, 5002, 6002, 'https://images.unsplash.com/photo-1501004318641-b39e6451bec6', 'Gel builder rosa en uñas', 0, true, CURRENT_TIMESTAMP),
  (7003, 5003, 6003, 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9', 'Acrílico blanco para uñas', 0, true, CURRENT_TIMESTAMP),
  (7004, 5004, 6004, 'https://images.unsplash.com/photo-1548082570-3cf8b9f8f9a7', 'Stickers florales para uñas', 0, true, CURRENT_TIMESTAMP),
  (7005, 5005, 6005, 'https://images.unsplash.com/photo-1504198453319-5ce911bafcde', 'Esmalte mate negro', 0, true, CURRENT_TIMESTAMP),
  (7006, 5006, 6006, 'https://images.unsplash.com/photo-1544025162-d76694265947', 'Esmalte rojo brillante', 0, true, CURRENT_TIMESTAMP),
  (7007, 5007, 6007, 'https://images.unsplash.com/photo-1505448735724-61b4f6a8be3b', 'Gel uv transparente', 0, true, CURRENT_TIMESTAMP),
  (7008, 5008, 6008, 'https://images.unsplash.com/photo-1519183071298-a2962be90bca', 'Pedicure spa con sales', 0, true, CURRENT_TIMESTAMP),
  (7009, 5009, 6009, 'https://images.unsplash.com/photo-1520975923025-4e5451b1d784', 'Tratamiento fortalecedor para uñas', 0, true, CURRENT_TIMESTAMP),
  (7010, 5010, 6010, 'https://images.unsplash.com/photo-1544025162-14bd1f6f0d5b', 'Pedrería para decoración de uñas', 0, true, CURRENT_TIMESTAMP);

-- ------------------------------------------------------------------
-- Warehouses (bodega) and inventory (saldo_inventario)
-- ------------------------------------------------------------------
INSERT INTO bodega (id_bodega, codigo, nombre, ciudad, codigo_pais, activo, creado_en)
VALUES
  (1, 'BOD-BOG', 'Bodega Bogotá', 'Bogotá', 'CO', true, CURRENT_TIMESTAMP),
  (2, 'BOD-MED', 'Bodega Medellín', 'Medellín', 'CO', true, CURRENT_TIMESTAMP),
  (3, 'BOD-CAL', 'Bodega Cali', 'Cali', 'CO', true, CURRENT_TIMESTAMP),
  (4, 'BOD-BAR', 'Bodega Barranquilla', 'Barranquilla', 'CO', true, CURRENT_TIMESTAMP),
  (5, 'BOD-BUC', 'Bodega Bucaramanga', 'Bucaramanga', 'CO', true, CURRENT_TIMESTAMP),
  (6, 'BOD-PEI', 'Bodega Pereira', 'Pereira', 'CO', true, CURRENT_TIMESTAMP),
  (7, 'BOD-MNZ', 'Bodega Manizales', 'Manizales', 'CO', true, CURRENT_TIMESTAMP),
  (8, 'BOD-CUC', 'Bodega Cúcuta', 'Cúcuta', 'CO', true, CURRENT_TIMESTAMP),
  (9, 'BOD-IBA', 'Bodega Ibagué', 'Ibagué', 'CO', true, CURRENT_TIMESTAMP),
  (10, 'BOD-CTG', 'Bodega Cartagena', 'Cartagena', 'CO', true, CURRENT_TIMESTAMP);

-- Inventory: associate each variant with a bodega and stock
INSERT INTO saldo_inventario (id_variante, id_bodega, cantidad_existencia, cantidad_reservada, nivel_reorden, actualizado_en)
VALUES
  (6001, 1, 50, 5, 10, CURRENT_TIMESTAMP),
  (6002, 1, 30, 2, 5, CURRENT_TIMESTAMP),
  (6003, 2, 40, 0, 8, CURRENT_TIMESTAMP),
  (6004, 2, 80, 8, 20, CURRENT_TIMESTAMP),
  (6005, 3, 120, 10, 30, CURRENT_TIMESTAMP),
  (6006, 3, 110, 11, 30, CURRENT_TIMESTAMP),
  (6007, 4, 25, 1, 5, CURRENT_TIMESTAMP),
  (6008, 5, 60, 4, 10, CURRENT_TIMESTAMP),
  (6009, 6, 45, 3, 8, CURRENT_TIMESTAMP),
  (6010, 7, 90, 6, 15, CURRENT_TIMESTAMP);

-- ------------------------------------------------------------------
-- Services (tipo_servicio, categoria_servicio, servicio) - 10 services
-- ------------------------------------------------------------------
INSERT INTO tipo_servicio (id_tipo_servicio, codigo, nombre, activo)
VALUES
  (1, 'SERVICIO', 'Servicio', true),
  (2, 'PRODUCTO', 'Producto', true);

INSERT INTO categoria_servicio (id_categoria_servicio, nombre, descripcion, activo)
VALUES
  (1, 'Manicure', 'Servicios de manicure', true),
  (2, 'Pedicure', 'Servicios de pedicure', true),
  (3, 'Decoración', 'Arte y decoración', true),
  (4, 'Tratamientos', 'Cuidado y salud', true);

INSERT INTO servicio (id_servicio, id_tipo_servicio, id_categoria_servicio, nombre, descripcion, duracion_minutos, precio_base, activo, creado_en)
VALUES
  (8001, 1, 1, 'Manicure Clásico', 'Corte, lima y esmalte clásico', 45, 40000.00, true, CURRENT_TIMESTAMP),
  (8002, 1, 1, 'Manicure Gel', 'Manicure con gel y acabado brillante', 60, 75000.00, true, CURRENT_TIMESTAMP),
  (8003, 1, 1, 'Manicure Acrílico', 'Uñas acrílicas completas', 90, 100000.00, true, CURRENT_TIMESTAMP),
  (8004, 1, 2, 'Pedicure Spa', 'Pedicure relajante con exfoliación', 60, 65000.00, true, CURRENT_TIMESTAMP),
  (8005, 1, 3, 'Decoración Premium', 'Diseño de uñas con pedrería', 45, 50000.00, true, CURRENT_TIMESTAMP),
  (8006, 1, 3, 'Arte Floral', 'Decoración floral detallada', 50, 52000.00, true, CURRENT_TIMESTAMP),
  (8007, 1, 4, 'Tratamiento Fortalecedor', 'Sérum fortalecedor profesional', 30, 42000.00, true, CURRENT_TIMESTAMP),
  (8008, 1, 2, 'Pedicure Express', 'Limpieza y esmalte rápido', 30, 30000.00, true, CURRENT_TIMESTAMP),
  (8009, 1, 1, 'Manicure Express', 'Lima y esmalte rápido', 25, 25000.00, true, CURRENT_TIMESTAMP),
  (8010, 1, 4, 'Tratamiento Hidratante de Cutículas', 'Cuidado intensivo de cutículas', 20, 20000.00, true, CURRENT_TIMESTAMP);

-- Assign some employees (perfil_empleado) — employees must reference existing usuario PKs
INSERT INTO perfil_empleado (id_usuario, codigo_empleado, fecha_contratacion, cargo, activo, notas, creado_en, actualizado_en)
VALUES
  (1001, 'EMP-001', '2022-01-10', 'Técnico Manicure', true, 'Experto en gel', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1002, 'EMP-002', '2022-03-05', 'Técnico Pedicure', true, 'Excelente atención al cliente', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1003, 'EMP-003', '2021-11-20', 'Técnico Decoración', true, 'Especialista en nail art', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1004, 'EMP-004', '2020-07-15', 'Supervisor', true, 'Supervisa turnos', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1005, 'EMP-005', '2019-05-01', 'Recepcionista', true, 'Atención y reservas', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1006, 'EMP-006', '2023-02-18', 'Técnico', true, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1007, 'EMP-007', '2023-06-30', 'Técnico', true, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1008, 'EMP-008', '2024-01-12', 'Técnico', true, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1009, 'EMP-009', '2024-08-21', 'Técnico', true, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (1028, 'EMP-010', '2018-09-01', 'Gerente', true, 'Gerente de sucursal', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Assign employees to services (empleado_servicio)
INSERT INTO empleado_servicio (id_usuario_empleado, id_servicio, duracion_personalizada_minutos, precio_personalizado, activo)
VALUES
  (1001, 8002, NULL, NULL, true),
  (1002, 8004, NULL, NULL, true),
  (1003, 8005, NULL, NULL, true),
  (1004, 8001, NULL, NULL, true),
  (1005, 8008, NULL, NULL, true),
  (1006, 8007, NULL, NULL, true),
  (1007, 8003, NULL, NULL, true),
  (1008, 8006, NULL, NULL, true),
  (1009, 8009, NULL, NULL, true),
  (1028, 8010, NULL, NULL, true);

COMMIT;

-- End of seed file
