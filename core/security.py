import hashlib
import logging

from django.core.cache import cache


SECURITY_LOGGER = logging.getLogger('nailsnice.security')


def get_client_ip(request):
    xff = (request.META.get('HTTP_X_FORWARDED_FOR') or '').strip()
    if xff:
        return xff.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR') or 'unknown').strip() or 'unknown'


def _rate_key(scope: str, identifier: str, kind: str):
    raw = f"{scope}:{identifier}".encode('utf-8', errors='ignore')
    digest = hashlib.sha256(raw).hexdigest()
    return f"security:{scope}:{kind}:{digest}"


def is_locked(scope: str, identifier: str):
    if not identifier:
        return False
    return bool(cache.get(_rate_key(scope, identifier, 'lock')))


def register_failure(
    scope: str,
    identifier: str,
    *,
    limit: int = 5,
    window_seconds: int = 300,
    lock_seconds: int = 900,
):
    if not identifier:
        return 0, False

    attempts_key = _rate_key(scope, identifier, 'attempts')
    attempts = int(cache.get(attempts_key, 0) or 0) + 1
    cache.set(attempts_key, attempts, timeout=window_seconds)

    locked = False
    if attempts >= limit:
        cache.set(_rate_key(scope, identifier, 'lock'), True, timeout=lock_seconds)
        locked = True

    return attempts, locked


def clear_failures(scope: str, identifier: str):
    if not identifier:
        return
    cache.delete(_rate_key(scope, identifier, 'attempts'))
    cache.delete(_rate_key(scope, identifier, 'lock'))


def security_event(event: str, request=None, *, extra=None, level='info'):
    payload = {
        'event': event,
        'path': getattr(request, 'path', None),
        'method': getattr(request, 'method', None),
        'ip': get_client_ip(request) if request is not None else None,
    }
    if extra:
        payload.update(extra)

    msg = f"security_event={payload}"
    log_fn = getattr(SECURITY_LOGGER, level, SECURITY_LOGGER.info)
    log_fn(msg)
