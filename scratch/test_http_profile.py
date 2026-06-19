import requests
import re

session = requests.Session()
login_url = "https://Profesional Beauty-render.onrender.com/login/"
profile_url = "https://Profesional Beauty-render.onrender.com/perfil/"

print("Visiting login page to get CSRF token...")
r = session.get(login_url)
print(f"Login page response: {r.status_code}")

# Extract csrfmiddlewaretoken using regex
match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
if not match:
    # Also check cookies
    csrf_token = session.cookies.get("csrftoken")
    if not csrf_token:
        print("Error: Could not find csrfmiddlewaretoken.")
        csrf_token = ""
    else:
        print(f"Found CSRF token in cookies: {csrf_token}")
else:
    csrf_token = match.group(1)
    print(f"Found CSRF token in HTML: {csrf_token}")

headers = {
    "Referer": login_url,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

data = {
    "csrfmiddlewaretoken": csrf_token,
    "correo": "testagent@example.com",
    "contrasena": "AgentPassword123!"
}

print("Submitting login form...")
r2 = session.post(login_url, data=data, headers=headers)
print(f"Login POST response: {r2.status_code}")
print(f"Current URL after login POST: {r2.url}")

# Now visit profile page
print("Visiting profile page...")
r3 = session.get(profile_url, headers=headers)
print(f"Profile page response: {r3.status_code}")
print(f"Profile content length: {len(r3.text)}")

if r3.status_code == 500:
    print("Error: Render profile page still returns 500!")
    print("\nPage preview:")
    print(r3.text[:1000])
elif r3.status_code == 200:
    print("Success: Render profile page loaded successfully with 200 OK.")
    if "Hola," in r3.text:
        print("User is logged in successfully.")
    else:
        print("WARNING: User might not be logged in or page contains unexpected content.")
        print(r3.text[:500])
else:
    print(f"Received status code {r3.status_code}.")
    print(r3.text[:500])
