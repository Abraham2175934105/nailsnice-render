#!/bin/bash
# Script de setup para NailsNice Django Backend

echo "🚀 NailsNice Django - Setup Inicial"
echo "===================================="

# Activar virtual environment
echo "1. Activando ambiente virtual..."
source venv/bin/activate

# Crear migraciones
echo "2. Creando migraciones..."
python manage.py makemigrations

# Aplicar migraciones
echo "3. Aplicando migraciones a BD..."
python manage.py migrate

# Crear superusuario interactivamente
echo "4. Creando superusuario..."
python manage.py createsuperuser

# Cargar datos iniciales (opcional)
echo "5. ¿Deseas cargar datos de prueba? (s/n)"
read -r load_data
if [ "$load_data" = "s" ]; then
    echo "Cargando fixtures..."
    # python manage.py loaddata seed_data.json
fi

echo "✓ Setup completado!"
echo ""
echo "Para iniciar el servidor:"
echo "  python manage.py runserver 8000"
echo ""
echo "Acceder al admin:"
echo "  http://localhost:8000/admin/"
