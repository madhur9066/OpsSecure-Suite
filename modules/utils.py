"""modules/utils.py — Shared decorators and helpers."""
from functools import wraps
from flask import abort
from flask_login import login_required, current_user


def role_required(role: str):
    """Decorator: user must be authenticated AND have the given role."""
    def wrapper(fn):
        @wraps(fn)
        @login_required
        def decorated(*args, **kwargs):
            if current_user.role != role:
                abort(403)
            return fn(*args, **kwargs)
        return decorated
    return wrapper
