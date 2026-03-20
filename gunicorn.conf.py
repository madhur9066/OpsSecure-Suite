# gunicorn.conf.py — Production WSGI configuration
# Run with:  gunicorn -c gunicorn.conf.py "run:app"
import multiprocessing
import os

# ── Workers ──────────────────────────────────────────────────
# Rule of thumb: (2 × CPU cores) + 1
workers     = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
threads     = 2
timeout     = 60
keepalive   = 5

# ── Binding ──────────────────────────────────────────────────
bind        = os.environ.get("GUNICORN_BIND", "0.0.0.0:5000")

# ── Logging ──────────────────────────────────────────────────
accesslog   = "logs/access.log"
errorlog    = "logs/error.log"
loglevel    = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── Process naming ───────────────────────────────────────────
proc_name   = "ssl_monitor"

# ── Security ─────────────────────────────────────────────────
limit_request_line   = 4094
limit_request_fields = 100
