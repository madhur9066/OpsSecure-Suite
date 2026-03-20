"""blueprints/certs.py — Certificate reader, matcher & self-signed generator."""
import io
import zipfile

from flask import Blueprint, render_template, request, current_app, send_file, jsonify
from flask_login import login_required
from modules.cert_reader    import parse_certificate
from modules.cert_matcher   import check_cert_key_match
from modules.cert_generator import generate_self_signed_cert

certs_bp = Blueprint("certs", __name__)

ALLOWED_CERT_EXTENSIONS = {".pem", ".crt", ".cer", ".der"}
ALLOWED_KEY_EXTENSIONS  = {".key", ".pem"}


def _ext(filename: str) -> str:
    import os
    return os.path.splitext(filename)[1].lower()


# ── Cert Reader ───────────────────────────────────────────────────────────
@certs_bp.route("/cert-reader", methods=["GET", "POST"])
#@login_required
def cert_reader():
    result = None
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            result = {"error": "Please upload a certificate file."}
        elif _ext(file.filename) not in ALLOWED_CERT_EXTENSIONS:
            result = {"error": "Unsupported file type. Upload a .pem/.crt/.cer/.der file."}
        else:
            try:
                data = parse_certificate(file)
                data["valid_from"] = str(data["valid_from"])
                data["expiry"]     = str(data["expiry"])
                result = data
            except Exception as exc:
                current_app.logger.warning("cert_reader error: %s", exc)
                result = {"error": str(exc)}

    return render_template("certs.html", result=result,
                           active_tab="reader", current_path=request.path)


# ── Cert Matcher ──────────────────────────────────────────────────────────
@certs_bp.route("/cert-match", methods=["GET", "POST"])
#@login_required
def cert_match():
    result = None
    if request.method == "POST":
        cert_file = request.files.get("cert")
        key_file  = request.files.get("key")

        if not cert_file or not key_file:
            result = {"error": "Upload both a certificate and a private key."}
        elif _ext(cert_file.filename) not in ALLOWED_CERT_EXTENSIONS:
            result = {"error": "Unsupported certificate type."}
        elif _ext(key_file.filename) not in ALLOWED_KEY_EXTENSIONS:
            result = {"error": "Unsupported key type."}
        else:
            try:
                result = check_cert_key_match(cert_file, key_file)
            except Exception as exc:
                current_app.logger.warning("cert_match error: %s", exc)
                result = {"error": str(exc)}

    return render_template("certs.html", result=result,
                           active_tab="matcher", current_path=request.path)


# ── Cert Generator — page ─────────────────────────────────────────────────
@certs_bp.route("/cert-generate", methods=["GET"])
#@login_required
def cert_generate():
    return render_template("certs.html", active_tab="generator",
                           current_path=request.path)


# ── Cert Generator — AJAX endpoint ───────────────────────────────────────
@certs_bp.route("/api/cert-generate", methods=["POST"])
#@login_required
def api_cert_generate():
    """
    Accepts JSON:
        common_name, org, country, state, locality,
        valid_days (int), key_size (int), san (comma-separated string)
    Returns a ZIP containing cert.pem + private.key
    """
    data = request.get_json(force=True)

    common_name = (data.get("common_name") or "").strip()
    if not common_name:
        return jsonify({"error": "Common Name (CN) is required."}), 400

    san_raw  = data.get("san", "")
    san_list = [s.strip() for s in san_raw.split(",") if s.strip()] if san_raw else []

    try:
        result = generate_self_signed_cert(
            common_name = common_name,
            org         = (data.get("org")      or "").strip(),
            country     = (data.get("country")  or "US").strip(),
            state       = (data.get("state")    or "").strip(),
            locality    = (data.get("locality") or "").strip(),
            valid_days  = int(data.get("valid_days", 365)),
            key_size    = int(data.get("key_size",   2048)),
            san_list    = san_list,
        )
    except Exception as exc:
        current_app.logger.warning("cert_generate error: %s", exc)
        return jsonify({"error": str(exc)}), 500

    # Pack cert + key into a ZIP in memory
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("cert.pem",    result["cert_pem"])
        zf.writestr("private.key", result["key_pem"])
    zip_buf.seek(0)

    safe_cn = common_name.replace(" ", "_").replace("/", "_")[:40]

    return send_file(
        zip_buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{safe_cn}_cert.zip",
    )


# ── Cert Generator — preview (returns JSON with PEM + summary) ────────────
@certs_bp.route("/api/cert-preview", methods=["POST"])
#@login_required
def api_cert_preview():
    """
    Same as api_cert_generate but returns JSON (cert_pem, key_pem, summary)
    instead of a file download. Used by the UI for individual file downloads.
    """
    data = request.get_json(force=True)

    common_name = (data.get("common_name") or "").strip()
    if not common_name:
        return jsonify({"error": "Common Name (CN) is required."}), 400

    san_raw  = data.get("san", "")
    san_list = [s.strip() for s in san_raw.split(",") if s.strip()] if san_raw else []

    try:
        result = generate_self_signed_cert(
            common_name = common_name,
            org         = (data.get("org")      or "").strip(),
            country     = (data.get("country")  or "US").strip(),
            state       = (data.get("state")    or "").strip(),
            locality    = (data.get("locality") or "").strip(),
            valid_days  = int(data.get("valid_days", 365)),
            key_size    = int(data.get("key_size",   2048)),
            san_list    = san_list,
        )
    except Exception as exc:
        current_app.logger.warning("cert_preview error: %s", exc)
        return jsonify({"error": str(exc)}), 500

    return jsonify({
        "cert_pem": result["cert_pem"],
        "key_pem":  result["key_pem"],
        "summary":  result["summary"],
    })