from django.utils.html import format_html, mark_safe

def build_bulk_import_message(procesados, exitosos, duplicados, fallidos, lista_duplicados=None, lista_fallidos=None):
    """
    Construye un mensaje HTML seguro para reportar el resultado de una carga masiva.
    """
    msg = f"<strong>¡Importación finalizada! 🎉</strong> Procesados: {procesados}, Exitosos: {exitosos}, Duplicados/Actualizados: {duplicados}, Fallidos: {fallidos}.<br>"
    
    if lista_duplicados:
        msg += "<strong>Duplicados/Actualizados:</strong><ul>"
        for d in lista_duplicados[:10]:
            msg += format_html("<li>{}</li>", str(d))
        if len(lista_duplicados) > 10:
            msg += format_html("<li>...y {} más.</li>", len(lista_duplicados) - 10)
        msg += "</ul>"
        
    if lista_fallidos:
        msg += "<strong>Fallidos:</strong><ul>"
        for f in lista_fallidos[:10]:
            msg += format_html("<li>{}</li>", str(f))
        if len(lista_fallidos) > 10:
            msg += format_html("<li>...y {} más.</li>", len(lista_fallidos) - 10)
        msg += "</ul>"
        
    return mark_safe(msg)
