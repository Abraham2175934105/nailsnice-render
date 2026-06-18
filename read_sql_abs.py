import re
import sys
import traceback

def main():
    try:
        filename = r'c:\Users\abrah\nails_nice_py\nails_nice\nails_nice_pyy\python\Nails_Nice_py\respaldo.sql'
        with open(filename, 'rb') as f:
            raw = f.read()
        enc = 'utf-16-le' if raw.startswith(b'\xff\xfe') else 'utf-8'
        content = raw.decode(enc, errors='replace')
        
        definitions = {}
        in_table = False
        current_table = ""
        table_lines = []
        
        for line in content.splitlines():
            m = re.search(r'CREATE TABLE\s+(?:public\.)?`?([A-Za-z0-9_]+)`?', line, re.IGNORECASE)
            if m:
                in_table = True
                current_table = m.group(1)
                table_lines = [line]
            elif in_table:
                table_lines.append(line)
                if ';' in line:
                    in_table = False
                    definitions[current_table] = "\n".join(table_lines)
                    
        # Filter and print matching tables
        for table, definition in definitions.items():
            t_lower = table.lower()
            if 'pedido' in t_lower or 'pago' in t_lower or 'transaccion' in t_lower or 'venta' in t_lower:
                print(f"=== TABLE: {table} ===")
                print(definition)
                print()
                
    except Exception as e:
        print("PYTHON_ERROR:")
        traceback.print_exc(file=sys.stdout)

if __name__ == '__main__':
    main()
