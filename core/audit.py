import datetime
import json
import logging
from decimal import Decimal
from typing import Any

from django.core.files.base import File
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Model
from django.db.models.fields.files import FieldFile

from .models import AuditLog

logger = logging.getLogger('Profesional Beauty')


def _normalize(value: Any):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, (UploadedFile, FieldFile, File)):
        return str(getattr(value, 'name', '') or value)
    if isinstance(value, Model):
        return {'model': value.__class__.__name__, 'pk': getattr(value, 'pk', None)}
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, set):
        return [_normalize(v) for v in value]

    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)

    return value


def record_audit(action: str, user=None, model: str = '', object_id: Any = None, data: Any = None):
    payload = _normalize(data or {})
    AuditLog.objects.create(
        action=action,
        model=model or '',
        object_id=str(object_id) if object_id is not None else '',
        actor=user if user and getattr(user, 'is_authenticated', False) else None,
        data=payload,
    )
    logger.info("audit %s %s#%s", action, model or '', object_id or '')


class AuditViewSetMixin:
    audit_prefix = ''

    def _audit(self, suffix: str, obj: Any, data: Any = None):
        action = f"{self.audit_prefix}.{suffix}" if self.audit_prefix else suffix
        record_audit(action, getattr(self, 'request', None) and getattr(self.request, 'user', None), obj.__class__.__name__, getattr(obj, 'pk', None), data)

    def perform_create(self, serializer):
        instance = serializer.save()
        self._audit('create', instance, serializer.validated_data)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._audit('update', instance, serializer.validated_data)

    def perform_destroy(self, instance):
        object_id = getattr(instance, 'pk', None)
        model_name = instance.__class__.__name__
        instance.delete()
        record_audit(
            f"{self.audit_prefix + '.' if self.audit_prefix else ''}delete",
            getattr(self, 'request', None) and getattr(self.request, 'user', None),
            model_name,
            object_id,
            {'deleted': True},
        )
