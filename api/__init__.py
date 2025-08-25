
"""Compatibility wrapper package.

Allows importing `api.app` by re-exporting from `apps.api.app`.
"""

from apps.api.app import app  # noqa: F401


