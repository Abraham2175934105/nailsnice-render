import re

def extract_table(filename, table_keyword):
    with open(filename, 'rb') as f:
        # Detect encoding
        raw = f.read()
        enc = 'utf-8'
        if raw.startswith(b'\xff\xfe'):
            enc = 'utf-16-le'
        content = raw.decode(enc, errors='replace')
        
    in_table = False
    table_def = []
    
    for line in content.splitlines():
        if re.search(r'CREATE TABLE.*' + table_keyword, line, re.IGNORECASE):
            in_table = True
            table_def.append(line)
        elif in_table:
            table_def.append(line)
            if ';' in line or line.startswith(')') and not line.strip() == ')':
                if line.strip() == ');':
                    break
                elif ';' in line:
                    break
    
    if table_def:
        print("\n".join(table_def))
    else:
        print(f"Table containing {table_keyword} not found.")

extract_table('respaldo.sql', 'direccion')
