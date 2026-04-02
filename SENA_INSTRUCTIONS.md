# 🎓 Guía de Despliegue Rápido - SENA

Sigue estos pasos para montar el proyecto en un PC nuevo:

1. **Preparar Base de Datos:**
   - Abrir XAMPP Control Panel.
   - Iniciar Apache y MySQL.
   - Ir a `http://localhost/phpmyadmin`.
   - Crear base de datos: `nails_nice`.
   - Importar el archivo `.sql` que traes en la USB.

2. **Configurar Python:**
   - Abrir la carpeta en VS Code.
   - Terminal: `python -m venv venv`
   - Terminal: `.\venv\Scripts\Activate.ps1`
   - Terminal: `pip install -r requirements.txt`

3. **Ajuste de Puerto (Si es necesario):**
   - Si el MySQL del SENA usa el puerto **3306**, cambia el valor en `nailsnice/settings.py` línea 94.

4. **Correr:**
   - `python manage.py runserver`

## 🧹 Limpieza antes de copiar a USB/Drive
Para que el proyecto pese menos y no lleves archivos que pueden dar error en otro PC:

1. **Listar carpetas temporales (Opcional):**
   `Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory`

2. **Borrar caché y entorno virtual (PowerShell):**
   ```powershell
   Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory | Remove-Item -Force -Recurse
   Remove-Item -Path venv, .venv -ErrorAction SilentlyContinue -Force -Recurse
   ```