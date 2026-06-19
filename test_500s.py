import os
import django
from django.test import Client
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from usuarios.models import Usuario

def test_views():
    client = Client()
    # Login as an admin
    admin_user = Usuario.objects.filter(correo='admin@profesionalbeauty.com').first()
    if not admin_user:
        admin_user = Usuario.objects.first()
        
    client.force_login(admin_user)

    urls_to_test = [
        '/gestion/crear/',
        '/catalogos/categoria/crear/',
        '/catalogos/marca/crear/',
    ]
    
    print("Testing GET requests to forms:")
    for url in urls_to_test:
        try:
            response = client.get(url)
            print(f"{url} -> Status: {response.status_code}")
            if response.status_code == 500:
                print(f"FAILED on {url}")
        except Exception as e:
            print(f"Exception on {url}: {str(e)}")

test_views()
