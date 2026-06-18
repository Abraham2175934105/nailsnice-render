import re

def list_tables(filename):
    with open(filename, 'rb') as f:
        # Detect encoding
        raw = f.read()
        enc = 'utf-8'
        if raw.startswith(b'\xff\xfe'):
            enc = 'utf-16-le'
        content = raw.decode(enc, errors='replace')
        
    tables = []
    for line in content.splitlines():
        m = re.search(r'CREATE TABLE\s+`?([A-Za-z0-9_]+)`?', line, re.IGNORECASE)
        if m:
            tables.append(m.group(1))
            
    with open('output_tables.txt', 'w', encoding='utf-8') as out:
        out.write("\n".join(tables))

list_tables('respaldo.sql')
