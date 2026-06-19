import os
import django
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Profesional Beauty.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.views import profile_view

User = get_user_model()
factory = RequestFactory()

print("--- RUNNING PROFILE_VIEW TEST FOR ALL USERS ---")
users = list(User.objects.all())
print(f"Testing {len(users)} users...")

for u in users:
    print(f"\nTesting User: ID={u.id_usuario}, Email={u.correo}")
    request = factory.get('/perfil/')
    request.user = u
    
    # Setup session
    from django.contrib.sessions.middleware import SessionMiddleware
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    
    try:
        response = profile_view(request)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 500:
            print("❌ 500 Error encountered!")
    except Exception as e:
        print("❌ CRITICAL ERROR IN profile_view:")
        traceback.print_exc(file=sys.stdout)
        print("-" * 40)
