"""
config.py — All app configuration loaded from environment variables.
Copy .env.example → .env and fill in your values. Never commit .env.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # ------------------------------------------------------------------ #
    # Core Flask
    # ------------------------------------------------------------------ #
    SECRET_KEY = os.environ.get("SECRET_KEY") or "CHANGE-ME-SET-IN-DOT-ENV"
    DEBUG = False
    TESTING = False

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    DB_PATH = os.environ.get("DB_PATH") or os.path.join(BASE_DIR, "ssl_monitor.db")

    # ------------------------------------------------------------------ #
    # Rate limiting  (flask-limiter)
    # ------------------------------------------------------------------ #
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = "memory://"        # swap to redis:// in prod

    # ------------------------------------------------------------------ #
    # Email / Alerts
    # ------------------------------------------------------------------ #
    SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.test.mail.com")
    SMTP_PORT   = int(os.environ.get("SMTP_PORT", 25))
    EMAIL_FROM  = os.environ.get("EMAIL_FROM", "test@mail.com")
    ALERT_TO    = os.environ.get("ALERT_TO", "test@mail.com")

    # ------------------------------------------------------------------ #
    # Scanner
    # ------------------------------------------------------------------ #
    SCAN_INTERVAL_MINUTES = int(os.environ.get("SCAN_INTERVAL_MINUTES", 5))
    ALERT_DAYS = [30, 20, 15, 10, 8, 6, 4, 3, 2, 1]

    # ------------------------------------------------------------------ #
    # Upload / file limits
    # ------------------------------------------------------------------ #
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024   # 2 MB max upload


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # In production, ensure SECRET_KEY is set via env var
    # and RATELIMIT_STORAGE_URL points to Redis


config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
