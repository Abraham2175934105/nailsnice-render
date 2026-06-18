import re

with open('respaldo.sql', 'rb') as f:
    raw = f.read()
    enc = 'utf-16-le' if raw.startswith(b'\xff\xfe') else 'utf-8'
    content = raw.decode(enc, errors='replace')

definitions = []
current_def = []
in_create = False

for line in content.splitlines():
    if re.search(r'CREATE TABLE', line, re.IGNORECASE):
        in_create = True
        current_def = [line]
    elif in_create:
        current_def.append(line)
        if ';' in line or line.strip() == ')':
            in_create = False
            definitions.append("\n".join(current_def))

with open('scratch/schema_output.txt', 'w', encoding='utf-8') as out:
    for d in definitions:
        if any(name in d.lower() for name in ['producto', 'variante', 'inventario', 'saldo']):
            out.write("="*60 + "\n")
            out.write(d + "\n")
