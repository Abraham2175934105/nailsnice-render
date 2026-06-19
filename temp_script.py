import os

files_to_update = [
    r"clientes/templates/clientes/cliente_list.html",
    r"servicios/templates/servicios/lista_servicios.html",
    r"servicios/templates/servicios/lista_empleado_servicios.html",
    r"inventario/templates/inventario/lista_movimientos.html"
]

base_dir = r"c:\Users\abrah\nails_nice_py\nails_nice\nails_nice_pyy\python\Nails_Nice_py"

for f in files_to_update:
    path = os.path.join(base_dir, os.path.normpath(f))
    if not os.path.exists(path):
        print(f"Skipping {path}, not found.")
        continue
    
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if "{% include 'partials/export_button.html' %}" in content:
        continue
        
    if '<div class="page-actions">' in content:
        content = content.replace('<div class="page-actions">', '<div class="page-actions">\n  {% include \'partials/export_button.html\' %}')
        with open(path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Updated {f}")
    else:
        print(f"Could not find <div class='page-actions'> in {f}")
