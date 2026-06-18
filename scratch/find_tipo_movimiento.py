import os

output_lines = []
try:
    with open('respaldo.sql', 'rb') as f:
        raw = f.read()
        enc = 'utf-16-le' if raw.startswith(b'\xff\xfe') else 'utf-8'
        content = raw.decode(enc, errors='replace')
    
    for line in content.splitlines():
        if 'tipo_movimiento_inventario' in line.lower():
            if 'insert' in line.lower() or 'create' in line.lower():
                output_lines.append(line[:500])
except Exception as e:
    output_lines.append(str(e))

raise RuntimeError("SEARCH_RESULTS:\n" + "\n".join(output_lines))
