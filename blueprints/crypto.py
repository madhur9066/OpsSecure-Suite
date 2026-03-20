"""blueprints/crypto.py — AES encrypt/decrypt, Base64, Secret vault"""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from cryptography.fernet import Fernet

from modules.crypto_utils import aes_encrypt, aes_decrypt, base64_encode, base64_decode, generate_key
from modules.db import SecretRepo

crypto_bp = Blueprint("crypto", __name__)


@crypto_bp.route("/crypto", methods=["GET", "POST"])
def crypto_page():
    output = key = None
    selected_tool = "password"

    if request.method == "POST":
        action        = request.form.get("action", "")
        key           = request.form.get("key", "").strip() or None
        selected_tool = request.form.get("selected_tool", "aes")
        try:
            if action in ("aes_encrypt", "aes_decrypt"):
                selected_tool = "aes"
                text = request.form.get("input_text", "")
                if action == "aes_encrypt":
                    if not key:
                        key = generate_key().decode()
                    output = aes_encrypt(text, key.encode())
                else:
                    output = aes_decrypt(text, key.encode()) if key else "⚠️ A key is required to decrypt."

            elif action in ("base64_encode", "base64_decode"):
                selected_tool = "base64"
                text   = request.form.get("input_text_b64", "")
                output = base64_encode(text) if action == "base64_encode" else base64_decode(text)

        except Exception as exc:
            current_app.logger.warning("crypto error action=%s: %s", action, exc)
            output = f"Error: {exc}"

    return render_template("crypto.html", output=output, key=key,
                           selected_tool=selected_tool, current_path=request.path)


@crypto_bp.route("/generate_key")
def generate_key_route():
    return Fernet.generate_key().decode()


@crypto_bp.route("/vault")
def vault():
    return render_template("vault.html", secrets=SecretRepo.all(),
                           current_path=request.path, page_title="Secret Vault")


@crypto_bp.route("/save_secret", methods=["POST"])
@login_required
def save_secret():
    name  = request.form.get("name",  "").strip()
    value = request.form.get("value", "").strip()
    if not name or not value:
        return jsonify({"error": "Both name and value are required."}), 400
    try:
        SecretRepo.create(name=name, encrypted_value=value)
        current_app.logger.info("Secret saved: %s by user=%s", name, current_user.username)
        return jsonify({"status": "saved"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@crypto_bp.route("/delete_secret/<int:secret_id>", methods=["POST"])
@login_required
def delete_secret(secret_id):
    try:
        SecretRepo.delete(secret_id)
        return jsonify({"status": "deleted"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
