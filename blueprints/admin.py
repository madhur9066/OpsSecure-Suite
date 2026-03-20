"""blueprints/admin.py — User management (admin role only)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user
from werkzeug.security import generate_password_hash

from modules.db import UserRepo
from modules.utils import role_required

admin_bp      = Blueprint("admin", __name__, url_prefix="/admin")
ALLOWED_ROLES = ("admin", "viewer")


@admin_bp.route("/users")
@role_required("admin")
def users():
    return render_template("admin/users.html",
                           users=UserRepo.all(order_by="id"),
                           current_path=request.path)


@admin_bp.route("/users/create", methods=["GET", "POST"])
@role_required("admin")
def create_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email",    "").strip()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm",  "").strip()
        role     = request.form.get("role",     "viewer").strip()

        errors = []
        if not username:              errors.append("Username is required.")
        if len(username) < 3:         errors.append("Username must be at least 3 characters.")
        if not password:              errors.append("Password is required.")
        if len(password) < 8:         errors.append("Password must be at least 8 characters.")
        if password != confirm:       errors.append("Passwords do not match.")
        if role not in ALLOWED_ROLES: errors.append("Invalid role selected.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/create_user.html",
                                   current_path=request.path, form=request.form)

        try:
            UserRepo.create(username=username, email=email,
                            password=generate_password_hash(password), role=role)
            current_app.logger.info("User created: %s (role=%s)", username, role)
            flash(f"User '{username}' created successfully.", "success")
            return redirect(url_for("admin.users"))
        except Exception as exc:
            flash(f"Username '{username}' already exists." if "UNIQUE" in str(exc)
                  else f"Error: {exc}", "danger")

    return render_template("admin/create_user.html", current_path=request.path, form={})


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@role_required("admin")
def reset_password(user_id):
    password = request.form.get("password", "").strip()
    confirm  = request.form.get("confirm",  "").strip()

    if not password or len(password) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return redirect(url_for("admin.users"))
    if password != confirm:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("admin.users"))

    row = UserRepo.get(user_id)
    if not row:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    UserRepo.update(user_id, password=generate_password_hash(password))
    current_app.logger.info("Password reset for user id=%s", user_id)
    flash(f"Password for '{row['username']}' updated successfully.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-role", methods=["POST"])
@role_required("admin")
def toggle_role(user_id):
    row = UserRepo.get(user_id)
    if not row:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))
    if row["username"] == current_user.username:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for("admin.users"))

    new_role = "viewer" if row["role"] == "admin" else "admin"
    UserRepo.update(user_id, role=new_role)
    flash(f"'{row['username']}' is now a {new_role}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user(user_id):
    row = UserRepo.get(user_id)
    if not row:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))
    if row["username"] == current_user.username:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin.users"))

    UserRepo.delete(user_id)
    current_app.logger.info("User deleted: %s", row["username"])
    flash(f"User '{row['username']}' deleted.", "success")
    return redirect(url_for("admin.users"))
