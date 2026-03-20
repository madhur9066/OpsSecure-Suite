"""
app_run.py — Entrypoint. Use gunicorn in production:
    gunicorn "run:app" -w 4 -b 0.0.0.0:5000
"""
import os
from app import create_app
from modules.scanner import start_background_scheduler

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    start_background_scheduler(app)
    app.run(port=5001, debug=app.config["DEBUG"], use_reloader=False)
