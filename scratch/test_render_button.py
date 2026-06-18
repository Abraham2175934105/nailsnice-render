import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from core.views import profile_view

User = get_user_model()
factory = RequestFactory()

# Get a user that has orders if possible, or just the first user
user = User.objects.first()
if not user:
    print("No users found.")
    sys.exit(0)

print(f"Rendering profile for User: {user.correo}")
request = factory.get('/perfil/')
request.user = user

from django.contrib.sessions.middleware import SessionMiddleware
middleware = SessionMiddleware(lambda req: None)
middleware.process_request(request)
request.session.save()

# Call the view to get the context
from django.shortcuts import render
# Mock render to capture context
context_data = {}
def mock_render(req, template, context=None, *args, **kwargs):
    global context_data
    context_data = context
    # Call original render
    return render(req, template, context, *args, **kwargs)

import core.views
original_render = core.views.render
core.views.render = mock_render

try:
    profile_view(request)
finally:
    core.views.render = original_render

# Render template to string using the captured context
html = render_to_string('perfil.html', context_data, request)

# Extract and print the button html
import re
buttons = re.findall(r'<button[^>]*data-toggle="pedido"[^>]*>.*?</button>', html, re.DOTALL)
print(f"Found {len(buttons)} 'Ver detalles' buttons:")
for idx, btn in enumerate(buttons):
    print(f"\n--- Button {idx+1} ---")
    print(btn)
