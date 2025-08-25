from apps.api.app import app  # re-export for gunicorn compatibility

__all__ = ["app"]