
"""Compatibility module to support legacy import path `api.app`.

This module simply re-exports the Flask application instance from
`apps.api.app` so that both `apps.api.app:app` and `api.app:app` work
with Gunicorn or other WSGI servers.
"""

from apps.api.app import app  # noqa: F401


