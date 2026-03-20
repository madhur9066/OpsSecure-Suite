"""app.py — Application factory."""
import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template
from flask_login import LoginManager, UserMixin
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config_map
from modules.db import init_db, UserRepo

csrf          = CSRFProtect()
limiter       = Limiter(key_func=get_remote_address)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


class User(UserMixin):
    def __init__(self, id, username, role):
        self.id       = id
        self.username = username
        self.role     = role


@login_manager.user_loader
def load_user(user_id):
    row = UserRepo.get(user_id)
    return User(row["id"], row["username"], row["role"]) if row else None


def create_app(env: str = "default") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_map[env])

    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    _configure_logging(app)

    with app.app_context():
        init_db()

    from blueprints.auth    import auth_bp
    from blueprints.main    import main_bp
    from blueprints.sites   import sites_bp
    from blueprints.certs   import certs_bp
    from blueprints.crypto  import crypto_bp
    from blueprints.tools   import tools_bp
    from blueprints.admin   import admin_bp
    from blueprints.network import network_bp

    for bp in (auth_bp, main_bp, sites_bp, certs_bp,
               crypto_bp, tools_bp, admin_bp, network_bp):
        app.register_blueprint(bp)

    _register_error_handlers(app)

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Frame-Options"]       = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"]       = "1; mode=block"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src  'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src   'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src    'self' data:;"
        )
        return response

    app.logger.info("OpsSecure started [env=%s]", env)
    return app


def _configure_logging(app):
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    fh  = RotatingFileHandler(os.path.join(log_dir, "ssl_monitor.log"),
                               maxBytes=10*1024*1024, backupCount=5)
    fh.setFormatter(fmt); fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.DEBUG if app.config["DEBUG"] else logging.INFO)
    app.logger.addHandler(fh)
    app.logger.addHandler(ch)
    app.logger.setLevel(logging.DEBUG if app.config["DEBUG"] else logging.INFO)


def _register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):       return render_template("errors/400.html"), 400
    @app.errorhandler(403)
    def forbidden(e):         return render_template("errors/403.html"), 403
    @app.errorhandler(404)
    def not_found(e):         return render_template("errors/404.html"), 404
    @app.errorhandler(429)
    def too_many(e):          return render_template("errors/429.html"), 429
    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Internal server error")
        return render_template("errors/500.html"), 500
