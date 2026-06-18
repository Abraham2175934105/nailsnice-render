import psycopg2
import sys

regions = ['oregon', 'ohio', 'frankfurt', 'singapore']
host_template = "dpg-d8pg2s5ckfvc73a89g4g-a.{}-postgres.render.com"

for region in regions:
    host = host_template.format(region)
    print(f"Trying region '{region}' (host: {host})...")
    try:
        conn = psycopg2.connect(
            host=host,
            database="nailsnice",
            user="admin",
            password="2O4M5jI0KvBVpo6fkwZd9l8S8bpQ0JgB",
            port=5432,
            connect_timeout=5
        )
        print(f"✅ Success! Connected to region: {region}")
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed: {e}\n")

print("Could not connect to any region.")
sys.exit(1)
