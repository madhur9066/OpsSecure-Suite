"""blueprints/auth.py — Login / Logout"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from modules.db import UserRepo

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    from app import limiter
    limiter.limit("10 per minute")(lambda: None)()

    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        row = UserRepo.find(username=username)
        if row and check_password_hash(row["password"], password):
            from app import User
            login_user(User(row["id"], row["username"], row["role"]), remember=False)
            current_app.logger.info("Login: user=%s ip=%s", username, request.remote_addr)
            return redirect(request.args.get("next") or url_for("main.index"))

        current_app.logger.warning("Failed login: user=%s ip=%s", username, request.remote_addr)
        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    current_app.logger.info("Logout: user=%s", current_user.username)
    logout_user()
    return redirect(url_for("main.index"))
