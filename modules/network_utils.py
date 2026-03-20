"""modules/network_utils.py — Core logic for Ping, DNS Lookup, IP Info, Port Scanner."""
import socket
import time
import json
import logging
import concurrent.futures
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

# ── Service map ───────────────────────────────────────────────────────────
SERVICE_MAP = {
    21: "FTP",        22: "SSH",         23: "Telnet",     25: "SMTP",
    53: "DNS",        80: "HTTP",        110: "POP3",      135: "RPC",
    139: "NetBIOS",   143: "IMAP",       443: "HTTPS",     445: "SMB",
    465: "SMTPS",     587: "SMTP/TLS",   993: "IMAPS",     995: "POP3S",
    1433: "MSSQL",    1521: "Oracle DB", 3000: "Node.js",  3306: "MySQL",
    3389: "RDP",      5432: "PostgreSQL",5900: "VNC",      6379: "Redis",
    8080: "HTTP-Alt", 8443: "HTTPS-Alt", 8888: "Jupyter",  9200: "Elasticsearch",
    27017: "MongoDB",
}

PORT_PRESETS = {
    "common": [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 3306, 3389, 5432, 8080, 8443],
    "web":    [80, 443, 3000, 4000, 5000, 8000, 8080, 8443, 9000],
    "db":     [1433, 1521, 3306, 5432, 6379, 9200, 27017],
    "mail":   [25, 110, 143, 465, 587, 993, 995],
}

MAX_CUSTOM_PORTS = 200


# ── Ping ──────────────────────────────────────────────────────────────────
def resolve_host(host: str) -> str | None:
    """Resolve hostname to IP. Returns None on failure."""
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None


def tcp_ping_once(ip: str, timeout: float = 3.0) -> float | None:
    """
    TCP connect-based ping. Tries ports 80 → 443 → 22 in order.
    Returns round-trip milliseconds, or None if all ports are unreachable.
    """
    for port in (80, 443, 22):
        try:
            t0 = time.perf_counter()
            with socket.create_connection((ip, port), timeout=timeout):
                pass
            return round((time.perf_counter() - t0) * 1000, 1)
        except (ConnectionRefusedError, OSError, socket.timeout):
            continue
    return None


def run_ping(host: str, count: int = 4) -> dict:
    """
    Ping *host* `count` times via TCP and return structured results.
    Returns {"error": "..."} on resolution failure.
    """
    count = max(1, min(count, 16))
    ip    = resolve_host(host)
    if not ip:
        return {"error": f"Cannot resolve hostname: {host}"}

    results = []
    for seq in range(1, count + 1):
        ms = tcp_ping_once(ip)
        results.append({"seq": seq, "ms": ms})
        logger.debug("ping seq=%d host=%s ip=%s ms=%s", seq, host, ip, ms)

    valid  = [r["ms"] for r in results if r["ms"] is not None]
    loss   = round((1 - len(valid) / count) * 100)

    return {
        "host":    host,
        "ip":      ip,
        "results": results,
        "summary": {
            "sent":     count,
            "received": len(valid),
            "loss_pct": loss,
            "min_ms":   min(valid)                          if valid else None,
            "avg_ms":   round(sum(valid) / len(valid))      if valid else None,
            "max_ms":   max(valid)                          if valid else None,
        },
    }


# ── DNS Lookup ────────────────────────────────────────────────────────────
DNS_STATUS = {
    0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL",
    3: "NXDOMAIN", 4: "NOTIMP", 5: "REFUSED",
}


def run_dns_lookup(host: str, record_type: str = "A") -> dict:
    """
    Query Google Public DNS (DoH) for *host* / *record_type*.
    Returns {"error": "..."} on failure.
    """
    record_type = record_type.upper()
    url = f"https://dns.google/resolve?name={host}&type={record_type}"

    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": "ToolKit/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())

        status_code = data.get("Status", -1)
        return {
            "host":      host,
            "type":      record_type,
            "status":    DNS_STATUS.get(status_code, f"UNKNOWN({status_code})"),
            "ok":        status_code == 0,
            "answers":   data.get("Answer",    []),
            "authority": data.get("Authority", []),
        }

    except urllib.error.URLError as exc:
        logger.warning("dns_lookup error host=%s type=%s: %s", host, record_type, exc)
        return {"error": str(exc)}
    except Exception as exc:
        logger.exception("dns_lookup unexpected error")
        return {"error": str(exc)}


# ── IP Info ───────────────────────────────────────────────────────────────
def run_ip_info(ip: str = "") -> dict:
    """
    Fetch geolocation and network info from ipapi.co.
    Pass empty string to look up the caller's own IP.
    Returns {"error": "..."} on failure.
    """
    url = f"https://ipapi.co/{ip}/json/" if ip else "https://ipapi.co/json/"

    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": "ToolKit/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())

        if data.get("error"):
            return {"error": data.get("reason", "Invalid IP address")}

        return {
            "ip":           data.get("ip"),
            "version":      data.get("version"),
            "city":         data.get("city"),
            "region":       data.get("region"),
            "country":      data.get("country_name"),
            "country_code": data.get("country_code"),
            "postal":       data.get("postal"),
            "latitude":     data.get("latitude"),
            "longitude":    data.get("longitude"),
            "timezone":     data.get("timezone"),
            "utc_offset":   data.get("utc_offset"),
            "org":          data.get("org"),
            "asn":          data.get("asn"),
        }

    except urllib.error.URLError as exc:
        logger.warning("ip_info error ip=%s: %s", ip, exc)
        return {"error": str(exc)}
    except Exception as exc:
        logger.exception("ip_info unexpected error")
        return {"error": str(exc)}


# ── Port Scanner ──────────────────────────────────────────────────────────
def _check_port(ip: str, port: int, timeout: float = 0.8) -> dict:
    """Check a single TCP port. Returns status: open | closed | filtered."""
    service = SERVICE_MAP.get(port, "—")
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return {"port": port, "service": service, "status": "open"}
    except ConnectionRefusedError:
        return {"port": port, "service": service, "status": "closed"}
    except socket.timeout:
        return {"port": port, "service": service, "status": "filtered"}
    except OSError:
        return {"port": port, "service": service, "status": "filtered"}


def run_port_scan(host: str, preset: str = "", start: int = 1,
                  end: int = 1024, max_workers: int = 50) -> dict:
    """
    Scan TCP ports on *host* concurrently.
    Uses *preset* if provided, otherwise scans start–end (capped at MAX_CUSTOM_PORTS).
    Returns {"error": "..."} on resolution failure.
    """
    ip = resolve_host(host)
    if not ip:
        return {"error": f"Cannot resolve hostname: {host}"}

    # Build port list
    if preset and preset in PORT_PRESETS:
        ports = PORT_PRESETS[preset]
    else:
        start = max(1, min(start, 65535))
        end   = max(start, min(end, 65535))
        if end - start + 1 > MAX_CUSTOM_PORTS:
            end = start + MAX_CUSTOM_PORTS - 1
        ports = list(range(start, end + 1))

    logger.info("port_scan host=%s ip=%s ports=%d", host, ip, len(ports))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures  = {executor.submit(_check_port, ip, p): p for p in ports}
        all_results = sorted(
            (f.result() for f in concurrent.futures.as_completed(futures)),
            key=lambda r: r["port"]
        )

    open_count     = sum(1 for r in all_results if r["status"] == "open")
    filtered_count = sum(1 for r in all_results if r["status"] == "filtered")
    closed_count   = sum(1 for r in all_results if r["status"] == "closed")

    return {
        "host":    host,
        "ip":      ip,
        "scanned": len(ports),
        "summary": {
            "open":     open_count,
            "filtered": filtered_count,
            "closed":   closed_count,
        },
        # Only return non-closed ports to keep payload lean
        "results": [r for r in all_results if r["status"] != "closed"],
    }