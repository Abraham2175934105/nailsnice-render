import os

def fix_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

base_dir = r"c:\Users\abrah\nails_nice_py\nails_nice\nails_nice_pyy\python\Nails_Nice_py"

# web/forms.py
fix_file(os.path.join(base_dir, r"web\forms.py"), [
    ("    fecha_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))\n", ""),
    ("            self.fields['fecha_nacimiento'].initial = perfil.fecha_nacimiento\n", ""),
    ("        perfil.fecha_nacimiento = data.get('fecha_nacimiento')\n", "")
])

# web/views.py
fix_file(os.path.join(base_dir, r"web\views.py"), [
    ("    ('fecha_nacimiento', 'Fecha nacimiento'),\n", ""),
    ("        'fecha_nacimiento': ('Fecha nacimiento', lambda c: c.fecha_nacimiento),\n", ""),
    ("            fecha_nacimiento = _as_text(row.get('fecha_nacimiento', ''))\n", ""),
    ("                'fecha_nacimiento': fecha_nacimiento,\n", "")
])

# web/templates/web/formulario.html
fix_file(os.path.join(base_dir, r"web\templates\web\formulario.html"), [
    ("            <label for=\"id_fecha_nacimiento\">Fecha de nacimiento</label>\n", ""),
    ("            {{ form.fecha_nacimiento }}\n", ""),
    ("            {% if form.fecha_nacimiento.errors %}<span class=\"badge-chip\">{{ form.fecha_nacimiento.errors }}</span>{% endif %}\n", "")
])

# web/templates/web/carga_masiva_clientes.html
fix_file(os.path.join(base_dir, r"web\templates\web\carga_masiva_clientes.html"), [
    ("Opcionales: fecha_nacimiento, acepta_fidelizacion", "Opcionales: acepta_fidelizacion")
])

# templates/clientes/cliente_list.html
fix_file(os.path.join(base_dir, r"templates\clientes\cliente_list.html"), [
    ("          <th>Fecha Nacimiento</th>\n", ""),
    ("          <td>{{ cliente.fecha_nacimiento|date:\"d M Y\"|default:\"—\" }}</td>\n", "")
])

# templates/clientes/cliente_form.html
fix_file(os.path.join(base_dir, r"templates\clientes\cliente_form.html"), [
    ("        <label for=\"{{ form.fecha_nacimiento.id_for_label }}\">Fecha de nacimiento</label>\n", ""),
    ("        {{ form.fecha_nacimiento }}\n", ""),
    ("        {% if form.fecha_nacimiento.errors %}<span class=\"form-error\">{{ form.fecha_nacimiento.errors.0 }}</span>{% endif %}\n", "")
])

# templates/clientes/cliente_detail.html
fix_file(os.path.join(base_dir, r"templates\clientes\cliente_detail.html"), [
    ("          <label for=\"{{ form.fecha_nacimiento.id_for_label }}\">Fecha de nacimiento</label>\n", ""),
    ("          {{ form.fecha_nacimiento }}\n", ""),
    ("          {% if form.fecha_nacimiento.errors %}<span class=\"form-error\">{{ form.fecha_nacimiento.errors.0 }}</span>{% endif %}\n", "")
])

# clientes/tests.py (we can just replace the whole test methods for patching fecha_nacimiento)
fix_file(os.path.join(base_dir, r"clientes\tests.py"), [
    ("        data = {'fecha_nacimiento': '1995-08-20'}\n", "        data = {'acepta_fidelizacion': False}\n"),
    ("        self.assertEqual(str(cliente_db.fecha_nacimiento), '1995-08-20')\n", "        self.assertEqual(cliente_db.acepta_fidelizacion, False)\n"),
    ("            'fecha_nacimiento': '1990-01-15',\n", "")
])

print('Done applying replacements')
