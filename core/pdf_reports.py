from datetime import date, datetime
from decimal import Decimal

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

# PARCHE SENIOR: Desactivamos weasyprint para permitir el despliegue local en Windows
# from weasyprint import HTML
HTML = None


def _format_cell(value):
    if value is None:
        return '-'

    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%d/%m/%Y %H:%M')

    if isinstance(value, date):
        return value.strftime('%d/%m/%Y')

    if isinstance(value, Decimal):
        return f"{value:,.2f}"

    return str(value)


def _resolve_user_label(request):
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return 'Sistema'

    full_name = ' '.join(filter(None, [
        getattr(user, 'nombre1', ''),
        getattr(user, 'apellido1', ''),
    ])).strip()

    if full_name:
        return full_name

    return getattr(user, 'email', None) or 'Sistema'


def build_crud_pdf_response(*, request, report_title: str, rows, filename: str):
    rows = rows or []
    headers = list(rows[0].keys()) if rows else []
    now_value = timezone.now()
    generated_at = timezone.localtime(now_value) if timezone.is_aware(now_value) else now_value
    document_code = f"NN-{generated_at.strftime('%Y%m%d-%H%M%S')}"

    table_rows = []
    for row in rows:
        table_rows.append([_format_cell(row.get(header)) for header in headers])

    context = {
        'company_name': 'Nails Nice',
        'company_nit': '900000000-0',
        'company_city': 'Bogota, Colombia',
        'company_email': 'info@nailsnice.com',
        'company_phone': '+57 300 123 4567',
        'report_title': report_title,
        'generated_at': generated_at,
        'generated_by': _resolve_user_label(request),
        'document_code': document_code,
        'record_count': len(rows),
        'headers': headers,
        'table_rows': table_rows,
        'legal_note': (
            'Documento de control interno generado automaticamente por Nails Nice. '
            'Su uso es administrativo y su distribucion debe estar autorizada.'
        ),
    }

    html_string = render_to_string('reportes/crud_export_pdf.html', context)
    
    # CONTROL DE ERRORES: Si HTML es None, devolvemos un mensaje amigable en vez de tumbar el servidor
    if HTML is None:
        return HttpResponse(
            "<h3>Exportación a PDF deshabilitada temporalmente en entorno local.</h3>"
            "<p>El motor gráfico GTK no está instalado en este sistema Windows.</p>",
            status=501
        )

    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/'),
    ).write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response