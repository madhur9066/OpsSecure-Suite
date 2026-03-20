"""blueprints/network.py — Routes for Network Tools (Ping, DNS, IP Info, Port Scanner)."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required

from modules.network_utils import run_ping, run_dns_lookup, run_ip_info, run_port_scan

network_bp = Blueprint("network", __name__)


# ── Page ─────────────────────────────────────────────────────────────────
@network_bp.route("/network")
#@login_required
def network_page():
    return render_template("network.html", current_path=request.path)


# ── API: Ping ─────────────────────────────────────────────────────────────
@network_bp.route("/api/ping", methods=["POST"])
#@login_required
def api_ping():
    data  = request.get_json(force=True)
    host  = (data.get("host") or "").strip()
    count = int(data.get("count", 4))

    if not host:
        return jsonify({"error": "Host is required"}), 400

    result = run_ping(host, count)
    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)


# ── API: DNS Lookup ───────────────────────────────────────────────────────
@network_bp.route("/api/dns", methods=["POST"])
#@login_required
def api_dns():
    data        = request.get_json(force=True)
    host        = (data.get("host") or "").strip()
    record_type = (data.get("type") or "A").strip()

    if not host:
        return jsonify({"error": "Host is required"}), 400

    result = run_dns_lookup(host, record_type)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


# ── API: IP Info ──────────────────────────────────────────────────────────
@network_bp.route("/api/ipinfo", methods=["POST"])
#@login_required
def api_ipinfo():
    data = request.get_json(force=True)
    ip   = (data.get("ip") or "").strip()

    result = run_ip_info(ip)
    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)


# ── API: Port Scanner ─────────────────────────────────────────────────────
@network_bp.route("/api/portscan", methods=["POST"])
#@login_required
def api_portscan():
    data   = request.get_json(force=True)
    host   = (data.get("host") or "").strip()
    preset = (data.get("preset") or "").strip()
    start  = int(data.get("start", 1))
    end    = int(data.get("end",   1024))

    if not host:
        return jsonify({"error": "Host is required"}), 400

    result = run_port_scan(host, preset, start, end)
    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)