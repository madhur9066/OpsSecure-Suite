"""modules/cert_checker.py — Live SSL certificate inspection.

Tries verified TLS first. If the cert is issued by an untrusted/internal CA
(e.g. Fortinet, self-signed, corporate PKI) it automatically retries with
verification disabled so internal sites still work.
"""
import ssl
import socket
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _fetch_cert(connect_host: str, server_hostname: str, verify: bool) -> dict:
    """Open a TLS connection and return the peer certificate dict."""
    if verify:
        context = ssl.create_default_context()
    else:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode    = ssl.CERT_NONE

    with socket.create_connection((connect_host, 443), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=server_hostname) as ssock:
            # getpeercert() returns empty dict when verify=False, so use
            # the binary DER form and parse it ourselves
            if verify:
                return ssock.getpeercert()
            else:
                der = ssock.getpeercert(binary_form=True)
                return _parse_der(der)


def _parse_der(der: bytes) -> dict:
    """Parse a DER certificate into the same shape as getpeercert()."""
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    cert = x509.load_der_x509_certificate(der, default_backend())

    # subject
    subject_cn = None
    try:
        subject_cn = cert.subject.get_attributes_for_oid(
            x509.NameOID.COMMON_NAME)[0].value
    except Exception:
        pass

    # issuer
    issuer_org = None
    issuer_cn  = None
    try:
        issuer_org = cert.issuer.get_attributes_for_oid(
            x509.NameOID.ORGANIZATION_NAME)[0].value
    except Exception:
        pass
    try:
        issuer_cn = cert.issuer.get_attributes_for_oid(
            x509.NameOID.COMMON_NAME)[0].value
    except Exception:
        pass

    # SAN
    san = []
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        san = ext.value.get_values_for_type(x509.DNSName)
    except Exception:
        pass

    # Build a getpeercert()-compatible dict
    not_after  = cert.not_valid_after
    not_before = cert.not_valid_before

    return {
        "notAfter":         not_after.strftime("%b %d %H:%M:%S %Y GMT"),
        "notBefore":        not_before.strftime("%b %d %H:%M:%S %Y GMT"),
        "subject":          (( ("commonName",      subject_cn or ""), ),),
        "issuer":           (( ("organizationName", issuer_org or issuer_cn or ""), ),),
        "subjectAltName":   [("DNS", s) for s in san],
        "serialNumber":     format(cert.serial_number, "X"),
        "version":          cert.version.value,
        "_unverified":      True,   # flag so callers know verification was skipped
    }


def get_cert_details(host: str, ip_override: str | None = None) -> dict:
    """
    Return certificate metadata for *host*, or {"error": "..."} on failure.
    Tries verified TLS first; falls back to unverified for internal/self-signed certs.
    """
    connect_host = ip_override or host
    unverified   = False

    try:
        cert = _fetch_cert(connect_host, host, verify=True)
    except ssl.SSLCertVerificationError as exc:
        # Internal / self-signed CA — retry without verification
        logger.warning(
            "TLS verification failed for %s (%s) — retrying unverified", host, exc
        )
        try:
            cert       = _fetch_cert(connect_host, host, verify=False)
            unverified = True
        except Exception as exc2:
            return {"error": str(exc2)}
    except socket.timeout:
        return {"error": f"Connection to {host} timed out"}
    except Exception as exc:
        return {"error": str(exc)}

    try:
        expiry     = datetime.strptime(cert["notAfter"],  "%b %d %H:%M:%S %Y %Z")
        valid_from = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
        days_left  = (expiry - datetime.utcnow()).days

        issuer  = dict(x[0] for x in cert.get("issuer",  []))
        subject = dict(x[0] for x in cert.get("subject", []))
        san     = [v for _, v in cert.get("subjectAltName", [])]

        return {
            "ip":            connect_host,
            "expiry":        expiry,
            "valid_from":    valid_from,
            "days_left":     days_left,
            "issuer":        issuer.get("organizationName") or issuer.get("commonName"),
            "common_name":   subject.get("commonName"),
            "san":           san,
            "serial_number": cert.get("serialNumber"),
            "version":       cert.get("version"),
            "unverified":    unverified,   # True = self-signed / untrusted CA
        }
    except Exception as exc:
        return {"error": f"Failed to parse certificate: {exc}"}