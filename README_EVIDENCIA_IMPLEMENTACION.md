# README de Evidencia Tecnica - Nails Nice

Fecha de corte: 2026-04-01  
Proyecto: Nails Nice (Django 4.2)

## 0. Panel de impacto (snapshot rapido)

| Indicador | Valor actual | Evidencia |
| --- | --- | --- |
| Fases de seguridad cerradas | 3 (F1, F2, F3) | [nailsnice/settings.py](nailsnice/settings.py#L54), [core/views.py](core/views.py#L180), [templates/perfil.html](templates/perfil.html#L123) |
| Middlewares de seguridad activos | 3 | [nailsnice/settings.py](nailsnice/settings.py#L99), [nailsnice/settings.py](nailsnice/settings.py#L100), [nailsnice/settings.py](nailsnice/settings.py#L103) |
| Modulos CRUD exportables a PDF | 5 | [inventario/views.py](inventario/views.py#L79), [productos/views.py](productos/views.py#L275), [pedidos/views.py](pedidos/views.py#L154), [servicios/views.py](servicios/views.py#L98), [web/views.py](web/views.py#L95) |
| Front premium reforzado | Home, Dashboard, Perfil, Login, Carrito | [templates/home.html](templates/home.html#L67), [templates/dashboard.html](templates/dashboard.html#L294), [templates/perfil.html](templates/perfil.html#L360), [templates/login.html](templates/login.html#L26), [templates/carrito.html](templates/carrito.html#L91) |
| Validacion tecnica de cierre | check + test core | [core/tests.py](core/tests.py#L1) |

## 1. Objetivo del documento

Este archivo consolida la evidencia tecnica de lo implementado recientemente en el proyecto.  
El objetivo es dejar una base clara para el equipo sobre:

- Que se construyo y que se corrigio.
- Cual es el nivel actual de seguridad y madurez tecnica.
- Que estandares de buenas practicas se estan cumpliendo.
- Como esta organizada la estructura del codigo y carpetas.
- Que falta para subir de nivel sin romper lo ya estable.

## 2. Resumen ejecutivo

El sistema esta en un estado funcional y estable para entorno academico/pyme, con un hardening real en autenticacion, sesiones y rutas protegidas.

Puntos fuertes actuales:

- Control de acceso anonimo por middleware.
- Bloqueo de intentos y anti-enumeracion en login y recuperacion.
- Sesiones endurecidas (flush, cycle_key, no-store, cookies httpOnly/samesite).
- Encabezados de seguridad base activos.
- Exportes PDF CRUD centralizados, con estilo corporativo y trazabilidad.
- Dashboard con payload robusto y graficas estables (sin render infinito).
- UX de perfil reforzada en FASE 3 con Centro de seguridad y estado de sesion.
- Normalizacion de imagenes y rutas media para evitar rupturas de render.
- Auditoria robusta con normalizacion de payload para archivos y objetos no serializables.

Limitaciones actuales:

- Cobertura de pruebas automatizadas aun baja (solo pruebas core puntuales).
- No hay evidencia de CSP estricta ni MFA.
- No hay pipeline formal de SAST/DAST ni metricas automatas de calidad.

Ruta recomendada de lectura para equipos:

1. Seguridad por fases (seccion 6).
2. Analisis funcional por modulo (seccion 7 y seccion 8).
3. Bitacora extendida de implementacion (seccion 14).
4. Matriz por archivo para sustentacion tecnica (seccion 15).

## 3. Nivel actual del proyecto (evaluacion interna)

Escala usada: 1 (basico) a 5 (avanzado).

| Dimension | Nivel | Estado resumido |
| --- | --- | --- |
| Seguridad de acceso y sesion | 4.0/5 | Hardening middleware + auth con rate limit y anti-enumeracion. |
| Arquitectura y modularidad | 3.8/5 | Separacion por apps Django y utilidades compartidas claras. |
| Calidad de frontend (UX/admin) | 4.0/5 | Mejoras premium en dashboard/perfil y manejo robusto de errores. |
| Reporteria y trazabilidad | 4.2/5 | Motor PDF comun con metadata y formato consistente. |
| Testing automatizado | 2.3/5 | Hay tests, pero la cobertura aun es corta para todo el sistema. |
| Operacion/observabilidad | 3.2/5 | Logging estructurado presente; faltan tableros/alertas formales. |

Diagnostico general: nivel intermedio-alto, con base solida para endurecer a nivel productivo formal.

## 4. Metodologia aplicada

Se aplico un enfoque incremental por fases, priorizando no romper negocio:

1. Diagnostico: revision de errores reales (frontend/backend), logs y rutas criticas.
2. Correccion dirigida: fix puntual por modulo (perfil, carrito, dashboard, PDF).
3. Hardening: controles de seguridad transversales en middleware/settings/auth.
4. UX de seguridad: mensajes y estado de sesion visibles al usuario.
5. Validacion: comandos de verificacion y pruebas para detectar regresiones.

Comandos validados en esta etapa:

- manage.py check -> sin issues.
- manage.py test core -> 2 tests OK.

## 5. Arquitectura y organizacion de carpetas

Estructura principal del proyecto en [Nails_Nice_py](.):

- [nailsnice](nailsnice): configuracion global (settings, urls, wsgi, asgi).
- [core](core): logica transversal (auth, middleware, seguridad, dashboard).
- [usuarios](usuarios): modelo de usuario/roles.
- [productos](productos): catalogo y CRUD de productos.
- [inventario](inventario): stock y operaciones de inventario.
- [pedidos](pedidos): pedidos, carrito, checkout, factura.
- [clientes](clientes): datos cliente.
- [servicios](servicios): servicios y agenda.
- [web](web): CRUD web complementario (clientes y reportes).
- [templates](templates): vistas HTML compartidas.
- [static](static): assets CSS/JS.

Organizacion por capas (practica observada):

- Capa presentacion: templates + CSS/JS.
- Capa aplicacion: views/forms/services.
- Capa dominio/datos: models + ORM Django.
- Capa transversal: seguridad, middleware, reportes PDF.

## 6. Seguridad implementada

### 6.1 FASE 1 - configuracion segura en settings

Evidencias:

- DEBUG por variable de entorno: [nailsnice/settings.py](nailsnice/settings.py#L54).
- SECRET_KEY por entorno + control de fallback seguro dev/prod: [nailsnice/settings.py](nailsnice/settings.py#L57).
- Registro de middlewares de seguridad: [nailsnice/settings.py](nailsnice/settings.py#L99), [nailsnice/settings.py](nailsnice/settings.py#L100), [nailsnice/settings.py](nailsnice/settings.py#L103).
- Cookies y sesion endurecidas: [nailsnice/settings.py](nailsnice/settings.py#L208), [nailsnice/settings.py](nailsnice/settings.py#L210), [nailsnice/settings.py](nailsnice/settings.py#L220).
- Headers base: [nailsnice/settings.py](nailsnice/settings.py#L224), [nailsnice/settings.py](nailsnice/settings.py#L225), [nailsnice/settings.py](nailsnice/settings.py#L226).

### 6.2 FASE 2 - hardening auth y recuperacion

Evidencias de controles:

- Mensajes genericos anti-enumeracion: [core/views.py](core/views.py#L37), [core/views.py](core/views.py#L39).
- Bloqueo por IP/identidad en login: [core/views.py](core/views.py#L180).
- Registro de fallos y locks de login: [core/views.py](core/views.py#L200).
- Limpieza de bloqueos en exito: [core/views.py](core/views.py#L205).
- Rotacion de sesion al login (session fixation mitigation): [core/views.py](core/views.py#L208).
- Cierre seguro en logout (flush): [core/views.py](core/views.py#L229).
- Bloqueo en flujo reset por IP/identidad: [core/views.py](core/views.py#L542).
- Decoy en recuperacion (sin revelar existencia): [core/views.py](core/views.py#L570).
- Motor central de rate limit/log seguridad: [core/security.py](core/security.py#L23), [core/security.py](core/security.py#L30), [core/security.py](core/security.py#L56).

### 6.3 Control de acceso y cache por middleware

- Guard de rutas anonimas (solo rutas publicas permitidas): [core/middleware.py](core/middleware.py#L8), [core/middleware.py](core/middleware.py#L18).
- No-store/no-cache en respuestas autenticadas: [core/middleware.py](core/middleware.py#L59), [core/middleware.py](core/middleware.py#L73).
- Headers de seguridad de respuesta: [core/middleware.py](core/middleware.py#L85), [core/middleware.py](core/middleware.py#L96).

### 6.4 FASE 3 - UX de seguridad en perfil/login

- Aviso de sesion expirada en login: [templates/login.html](templates/login.html#L26).
- Security info de sesion/IP desde backend de perfil: [core/views.py](core/views.py#L424).
- Panel Centro de seguridad en perfil: [templates/perfil.html](templates/perfil.html#L123).
- Countdown de expiracion de sesion en frontend: [templates/perfil.html](templates/perfil.html#L477).

Evaluacion de FASE 3: completada a nivel UX funcional, sin alterar logica de negocio.

## 7. Analisis funcional de la aplicacion web

### 7.1 Dashboard administrativo

Implementaciones relevantes:

- Umbral de stock bajo con criterio <= threshold: [core/views.py](core/views.py#L138).
- Payload de graficas centralizado en context: [core/views.py](core/views.py#L145).
- Entrega segura de datos a JS via json_script: [templates/dashboard.html](templates/dashboard.html#L294).
- Destruccion previa de instancias Chart para evitar loops/infinite stretch: [templates/dashboard.html](templates/dashboard.html#L349), [templates/dashboard.html](templates/dashboard.html#L392), [templates/dashboard.html](templates/dashboard.html#L429).

### 7.2 Perfil de usuario

Mejoras UX + robustez:

- Prevencion de bug por colision de form.action: [templates/perfil.html](templates/perfil.html#L360).
- Verificacion content-type para evitar errores JSON inesperados: [templates/perfil.html](templates/perfil.html#L372).
- Manejo explicito de sesion expirada en AJAX: [templates/perfil.html](templates/perfil.html#L376).

### 7.3 Carrito

- Correccion de render de imagen usando ImageField.url: [templates/carrito.html](templates/carrito.html#L91).
- Placeholder/fallback de imagen en error de carga: [templates/carrito.html](templates/carrito.html#L92).

## 8. Reporteria PDF y trazabilidad documental

Implementacion central:

- Helper compartido para CRUD PDF: [core/pdf_reports.py](core/pdf_reports.py#L44).
- Normalizacion de celdas (fechas, decimales, nulos): [core/pdf_reports.py](core/pdf_reports.py#L10).
- Manejo seguro aware/naive datetime para evitar crash: [core/pdf_reports.py](core/pdf_reports.py#L15), [core/pdf_reports.py](core/pdf_reports.py#L48).
- Plantilla corporativa premium: [templates/reportes/crud_export_pdf.html](templates/reportes/crud_export_pdf.html#L1).

Integracion en CRUDs:

- Inventario: [inventario/views.py](inventario/views.py#L79).
- Productos: [productos/views.py](productos/views.py#L275).
- Servicios: [servicios/views.py](servicios/views.py#L98).
- Pedidos (reporte CRUD): [pedidos/views.py](pedidos/views.py#L154).
- Clientes web: [web/views.py](web/views.py#L95).

Nota: la factura comercial de pedido sigue flujo propio separado (no se mezclo con CRUD export).

## 9. Estandares y buenas practicas que se cumplen (estado actual)

Tabla de cumplimiento orientativa (no certificacion externa):

| Referencia | Cobertura observada | Estado |
| --- | --- | --- |
| OWASP - Control de acceso | Middleware guard + admin_required en vistas administrativas | Parcial-alto |
| OWASP - Autenticacion segura | Rate limiting, anti-enumeracion, cycle_key, flush | Alto |
| OWASP - Security misconfiguration | Headers, cookies seguras, samesite, no-store | Alto |
| OWASP - Integridad de sesion | Expiracion de sesion + renovacion de llave | Alto |
| OWASP - Logging de eventos de seguridad | Eventos de seguridad en auth/reset | Parcial-alto |
| Django Security Best Practices | CSRF middleware, auth decorators, ORM, X-Frame, nosniff | Alto |
| API hygiene DRF | Endpoints estructurados y paginacion base | Parcial |

## 10. Nivel de programacion y calidad tecnica

Evaluacion cualitativa del codigo reciente:

- Backend: intermedio-alto (patrones claros, reutilizacion helper, controles de seguridad reales).
- Frontend templates: intermedio-alto (UX mejorada, manejo de errores, accesibilidad basica).
- Diseño de datos: intermedio (coexistencia de modelo nuevo y legacy bien resuelta, pero aumenta complejidad).
- Testing: basico-intermedio (hay pruebas criticas, falta ampliar cobertura por app).

Fortalezas:

- Modularidad por apps.
- Reuso (pdf_reports, security helpers, middleware).
- Cambios con foco en regresion minima.

Pendiente para subir nivel:

- Mayor cobertura de tests (auth, middleware, dashboard, carrito, exportes).
- Linters/formatters y analisis estatico automatico en CI.
- Politica CSP y endurecimiento adicional de cabeceras.

## 11. Evidencia de pruebas y validacion

Resultado de validaciones ejecutadas:

- manage.py check: sin issues de sistema.
- manage.py test core: 2 pruebas ejecutadas, OK.

Casos cubiertos actualmente en core:

- Cambio de contrasena exitoso en perfil.
- Rechazo de contrasena debil.

Referencia de tests: [core/tests.py](core/tests.py#L1).

## 12. Riesgos residuales y plan recomendado

Riesgos residuales:

- Cobertura de pruebas todavia limitada para una salida productiva formal.
- No hay MFA para cuentas administrativas.
- Falta validacion automatica de seguridad en pipeline (SAST/DAST).

Plan recomendado (proxima iteracion):

1. Crear bateria de tests por modulo (pedidos, inventario, middleware, auth reset).
2. Agregar CSP y politicas de cabeceras avanzadas por entorno.
3. Agregar monitoreo de seguridad con alertas por eventos criticos.
4. Definir checklist release (check, tests, exportes PDF, smoke UI).

## 13. Mapa rapido de archivos clave

Seguridad:

- [nailsnice/settings.py](nailsnice/settings.py)
- [core/middleware.py](core/middleware.py)
- [core/security.py](core/security.py)
- [core/views.py](core/views.py)
- [core/auth.py](core/auth.py)

UI/UX:

- [templates/perfil.html](templates/perfil.html)
- [static/css/profile.css](static/css/profile.css)
- [templates/login.html](templates/login.html)
- [templates/dashboard.html](templates/dashboard.html)
- [templates/carrito.html](templates/carrito.html)

Reporteria:

- [core/pdf_reports.py](core/pdf_reports.py)
- [templates/reportes/crud_export_pdf.html](templates/reportes/crud_export_pdf.html)
- [inventario/views.py](inventario/views.py)
- [productos/views.py](productos/views.py)
- [pedidos/views.py](pedidos/views.py)
- [servicios/views.py](servicios/views.py)
- [web/views.py](web/views.py)

## 14. Bitacora cronologica ampliada (implementado en el chat)

### 14.1 Estabilizacion funcional inicial

- Se corrigio la serializacion de auditoria para soportar archivos/campos no JSON nativos.
	Evidencia: [core/audit.py](core/audit.py#L17), [core/audit.py](core/audit.py#L22), [core/audit.py](core/audit.py#L42).
- Se robustecio el pipeline de imagenes para evitar rutas inconsistentes y duplicadas.
	Evidencia backend: [productos/views.py](productos/views.py#L27), [productos/views.py](productos/views.py#L88), [productos/serializers.py](productos/serializers.py#L68), [productos/serializers.py](productos/serializers.py#L105).
- Se corrigio el render de imagen en carrito con fallback visual.
	Evidencia: [templates/carrito.html](templates/carrito.html#L91), [templates/carrito.html](templates/carrito.html#L92).
- Se corrigio el bug AJAX de perfil por colision con action en formulario.
	Evidencia: [templates/perfil.html](templates/perfil.html#L360), [templates/perfil.html](templates/perfil.html#L372).

### 14.2 Consolidacion analitica (dashboard)

- Se unifico payload de graficas con json_script y parseo seguro.
	Evidencia: [core/views.py](core/views.py#L145), [templates/dashboard.html](templates/dashboard.html#L294).
- Se ajusto regla de stock bajo a <= umbral para casos frontera.
	Evidencia: [core/views.py](core/views.py#L35), [core/views.py](core/views.py#L138).
- Se elimino riesgo de estiramiento/infinite render destruyendo instancias previas de Chart.
	Evidencia: [templates/dashboard.html](templates/dashboard.html#L349), [templates/dashboard.html](templates/dashboard.html#L392), [templates/dashboard.html](templates/dashboard.html#L429).

### 14.3 Reporteria documental premium

- Se creo helper transversal para exportes PDF CRUD con metadata corporativa.
	Evidencia: [core/pdf_reports.py](core/pdf_reports.py#L44), [core/pdf_reports.py](core/pdf_reports.py#L49), [core/pdf_reports.py](core/pdf_reports.py#L74).
- Se soluciono riesgo por datetimes naive/aware en formateo.
	Evidencia: [core/pdf_reports.py](core/pdf_reports.py#L15), [core/pdf_reports.py](core/pdf_reports.py#L48).
- Se publico plantilla premium con paginado, pie legal y branding.
	Evidencia: [templates/reportes/crud_export_pdf.html](templates/reportes/crud_export_pdf.html#L1).

### 14.4 Endurecimiento por fases de seguridad

- FASE 1: settings por entorno y politicas base de sesion/cookies/headers.
	Evidencia: [nailsnice/settings.py](nailsnice/settings.py#L54), [nailsnice/settings.py](nailsnice/settings.py#L57), [nailsnice/settings.py](nailsnice/settings.py#L208), [nailsnice/settings.py](nailsnice/settings.py#L224).
- FASE 2: rate-limit, anti-enumeracion, decoy reset, logging de eventos.
	Evidencia: [core/views.py](core/views.py#L180), [core/views.py](core/views.py#L200), [core/views.py](core/views.py#L542), [core/views.py](core/views.py#L570), [core/security.py](core/security.py#L30), [core/security.py](core/security.py#L56).
- FASE 3: UX de seguridad visible para usuario final.
	Evidencia: [templates/login.html](templates/login.html#L26), [templates/perfil.html](templates/perfil.html#L123), [templates/perfil.html](templates/perfil.html#L477).

### 14.5 Compatibilidad de datos y operacion legacy

- Checkout valida direccion colombiana y prefill inteligente por historico/cliente.
	Evidencia: [pedidos/views.py](pedidos/views.py#L40), [pedidos/views.py](pedidos/views.py#L47), [pedidos/views.py](pedidos/views.py#L381).
- Sincronizacion dual de pedidos (modelo nuevo + legacy) para continuidad operativa.
	Evidencia: [pedidos/views.py](pedidos/views.py#L420), [pedidos/services.py](pedidos/services.py#L42), [pedidos/services.py](pedidos/services.py#L67), [pedidos/services.py](pedidos/services.py#L70).

## 15. Matriz detallada de cambios por archivo

| Archivo | Implementacion clave | Impacto obtenido |
| --- | --- | --- |
| [core/middleware.py](core/middleware.py) | Guard anonimo + no-store + headers de seguridad | Cierre de acceso indebido y menor exposicion en navegador |
| [nailsnice/settings.py](nailsnice/settings.py) | Variables de entorno para DEBUG/SECRET_KEY y hardening de sesion | Configuracion mas segura y portable |
| [core/security.py](core/security.py) | Keys hash de rate-limit, lock y eventos de seguridad | Mitigacion de fuerza bruta y trazabilidad |
| [core/views.py](core/views.py) | Login/reset endurecido, dashboard robusto, security_info perfil | Flujo auth mas seguro + panel admin estable |
| [templates/perfil.html](templates/perfil.html) | AJAX robusto + Centro de seguridad + countdown sesion | Mejor UX y menos errores de cliente |
| [static/css/profile.css](static/css/profile.css) | Estilos premium y panel de seguridad F3 | Claridad visual del estado de seguridad |
| [templates/login.html](templates/login.html) | Mensaje de sesion expirada por seguridad | Mejor guia al usuario tras timeout/logout |
| [templates/dashboard.html](templates/dashboard.html) | Chart.js seguro, destroy de instancias, wrappers estables | Sin deformaciones ni re-render inestable |
| [core/pdf_reports.py](core/pdf_reports.py) | Motor unico de export PDF CRUD | Estandarizacion documental transversal |
| [templates/reportes/crud_export_pdf.html](templates/reportes/crud_export_pdf.html) | Plantilla branded premium | Evidencia administrativa legible y profesional |
| [pedidos/services.py](pedidos/services.py) | Crear pedido nuevo + sync legacy + audit | Continuidad funcional sin romper integraciones |
| [pedidos/views.py](pedidos/views.py) | Checkout validado y prefill de direccion | Menos friccion de compra y datos consistentes |
| [productos/serializers.py](productos/serializers.py) | Normalizacion de imagen para API | Menos fallos de imagen en frontend |
| [productos/views.py](productos/views.py) | Resolucion robusta de imagenes en vistas | Render confiable en catalogo y detalle |
| [templates/carrito.html](templates/carrito.html) | Uso de imagen.url + placeholder onerror | Carrito visualmente estable |
| [core/audit.py](core/audit.py) | Normalizador de payload para archivos/modelos/decimales | Evita errores de serializacion y mejora auditoria |
| [templates/home.html](templates/home.html) | Hero premium + sticky search + greeting card | Home mas moderna y orientada a conversion |
| [static/css/style.css](static/css/style.css) | Sistema visual y layout responsivo mejorado | Identidad visual mas fuerte y consistente |

## 16. Analisis de arquitectura y nivel de programacion (ampliado)

Patrones tecnicos observables:

- Patron transversal de utilidades compartidas:
	PDF ([core/pdf_reports.py](core/pdf_reports.py#L44)), seguridad ([core/security.py](core/security.py#L30)), auditoria ([core/audit.py](core/audit.py#L42)).
- Patron de defensa en profundidad:
	settings + middleware + vistas auth + UX informativa.
- Patron de compatibilidad evolutiva:
	coexistencia modelo nuevo/legacy en pedidos sin interrumpir operacion ([pedidos/services.py](pedidos/services.py#L42), [pedidos/services.py](pedidos/services.py#L70)).
- Patron de frontend resiliente:
	validacion de content-type, fallback visual, destruccion controlada de instancias JS.

Lectura de madurez:

- Nivel de programacion del proyecto: intermedio-alto con decisiones de ingenieria orientadas a estabilidad real.
- Nivel de organizacion: bueno, por separacion en apps y capas transversales reutilizables.
- Nivel de mantenibilidad: bueno, aunque se recomienda ampliar pruebas y automatizacion de calidad.

## 17. Estandares cumplidos (detalle ampliado para sustentacion)

Checklist practico de cumplimiento observado:

- Control de acceso por autenticacion y rol en vistas administrativas:
	[core/auth.py](core/auth.py#L14), [core/views.py](core/views.py#L67), [pedidos/views.py](pedidos/views.py#L162), [web/views.py](web/views.py#L111).
- Mitigacion de fijacion y secuestro de sesion:
	[core/views.py](core/views.py#L208), [core/views.py](core/views.py#L229), [core/middleware.py](core/middleware.py#L73).
- Manejo seguro de cabeceras y privacidad:
	[core/middleware.py](core/middleware.py#L96), [nailsnice/settings.py](nailsnice/settings.py#L224).
- Trazabilidad de eventos de seguridad y auditoria de cambios:
	[core/security.py](core/security.py#L56), [core/audit.py](core/audit.py#L42).
- Defensa de calidad de datos en checkout/perfil:
	[pedidos/views.py](pedidos/views.py#L40), [templates/perfil.html](templates/perfil.html#L372).

## 18. Guia de uso para companeros (evidencia rapida)

Si tu equipo necesita revisar todo sin perderse, esta es la ruta corta:

1. Seguridad completa: seccion 6 + seccion 17.
2. Cambios implementados y donde estan: seccion 14 + seccion 15.
3. Estado tecnico y nivel del proyecto: seccion 3 + seccion 16.
4. Riesgos y siguiente iteracion: seccion 12.

Esta guia permite sustentar el trabajo tecnico ante companeros, docentes o revisores sin leer todo el historial del chat.

---

Documento elaborado para uso interno del equipo tecnico y companeros del proyecto.
