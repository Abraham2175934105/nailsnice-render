#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# =========================================================================
# PARCHE MAESTRO SENIOR: Inyección de Mock Global para WeasyPrint en Windows
# =========================================================================
class FakeWeasyPrintHTML:
    def __init__(self, *args, **kwargs):
        pass
    def write_pdf(self, *args, **kwargs):
        return b"PDF deshabilitado localmente"

class FakeWeasyPrintModule:
    HTML = FakeWeasyPrintHTML

# Forzamos a Python a creer que WeasyPrint ya está cargado en memoria de manera simulada
sys.modules['weasyprint'] = FakeWeasyPrintModule
# =========================================================================


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()