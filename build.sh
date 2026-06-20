#!/usr/bin/env bash
# exit on error
set -o errexit

echo "📦 Instalando dependencias..."
pip install -r requirements.txt

echo "🎨 Recolectando archivos estáticos..."
rm -rf staticfiles_build
python manage.py collectstatic --noinput --clear

# NOTA: Las migraciones NO se ejecutan aquí porque en la fase de Build
# Render no permite conexión al host interno de la base de datos.
# Se deben ejecutar en el Start Command.
echo "✅ Build finalizado exitosamente."
