"""blueprints/sites.py — Site management"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user

from modules.db import SiteRepo, ResultRepo
from modules.cert_checker import get_cert_details
from modules.utils import role_required

sites_bp = Blueprint("sites", __name__)


@sites_bp.route("/sites")
def list_sites():
    return render_template("sites.html",
                           sites=SiteRepo.list_with_results(),
                           stats=ResultRepo.get_stats(),
                           current_path=request.path)


@sites_bp.route("/add-site", methods=["GET", "POST"])
@role_required("admin")
def add_site():
    result = None
    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        url         = request.form.get("url",  "").strip()
        ip_override = request.form.get("ip_override", "").strip() or None
        action      = request.form.get("action")

        if not url:
            flash("URL is required.", "danger")
            return render_template("add_site.html", result=None, current_path=request.path)

        if action == "validate":
            result = get_cert_details(url, ip_override)

        elif action == "save":
            if not name:
                flash("Name is required to save.", "danger")
                return render_template("add_site.html", result=None, current_path=request.path)
            try:
                data = get_cert_details(url, ip_override)
                if "error" in data:
                    flash(f"SSL Error: {data['error']}", "danger")
                    return render_template("add_site.html", result=data, current_path=request.path)

                SiteRepo.upsert(name, url, ip_override)
                ResultRepo.upsert(url, data["ip"], str(data["expiry"]), data["days_left"])

                current_app.logger.info("Site saved: %s by user=%s", url, current_user.username)
                flash(f"Site '{name}' saved successfully.", "success")
                return redirect(url_for("sites.list_sites"))

            except Exception as exc:
                current_app.logger.exception("Error saving site %s", url)
                flash(f"Unexpected error: {exc}", "danger")

    return render_template("add_site.html", result=result, current_path=request.path)


@sites_bp.route("/cert-details")
def cert_details():
    site = request.args.get("site", "").strip()
    if not site:
        return jsonify({"error": "No site provided"}), 400

    row         = SiteRepo.find(url=site)
    ip_override = row["ip_override"] if row else None
    data        = get_cert_details(site, ip_override)
    if "error" not in data:
        data["expiry"]     = str(data["expiry"])
        data["valid_from"] = str(data["valid_from"])
    return jsonify(data)


@sites_bp.route("/validate-ssl", methods=["POST"])
def validate_ssl_api():
    from urllib.parse import urlparse
    try:
        body        = request.get_json(force=True, silent=True) or {}
        url         = body.get("url", "").strip()
        ip_override = body.get("ip_override", "").strip() or None

        if not url:
            return jsonify({"error": "URL is required"}), 400
        if not url.startswith("http"):
            url = "https://" + url

        hostname = urlparse(url).hostname
        if not hostname:
            return jsonify({"error": "Could not parse hostname"}), 400

        data = get_cert_details(hostname, ip_override)
        if "error" in data:
            return jsonify(data), 500

        return jsonify({
            "ip":          data["ip"],
            "common_name": data["common_name"],
            "issuer":      data["issuer"],
            "expiry":      str(data["expiry"]),
            "days_left":   data["days_left"],
            "unverified":  data.get("unverified", False),
        })
    except Exception as exc:
        current_app.logger.warning("validate-ssl error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@sites_bp.route("/delete-site", methods=["POST"])
@role_required("admin")
def delete_site():
    url = request.form.get("url", "").strip()
    if not url:
        return jsonify({"error": "No site provided"}), 400
    try:
        SiteRepo.delete_by_url(url)
        current_app.logger.info("Site deleted: %s by user=%s", url, current_user.username)
        return jsonify({"status": "deleted"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@sites_bp.route("/malware-scan")
@login_required
def malware_scan():
    site = request.args.get("site", "").strip()
    if not site:
        return jsonify({"error": "No site provided"}), 400
    from modules.malware_checker import basic_scan
    return jsonify(basic_scan(site))
