"""modules/cert_generator.py — Self-signed certificate generation using cryptography library."""
import ipaddress
import logging
from datetime import datetime, timezone, timedelta

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger(__name__)


def generate_self_signed_cert(
    common_name:   str,
    org:           str        = "",
    country:       str        = "US",
    state:         str        = "",
    locality:      str        = "",
    valid_days:    int        = 365,
    key_size:      int        = 2048,
    san_list:      list[str]  = None,
) -> dict:
    """
    Generate a self-signed certificate and RSA private key.

    Returns a dict with:
        cert_pem  (str)  — PEM-encoded certificate
        key_pem   (str)  — PEM-encoded private key (PKCS8, unencrypted)
        summary   (dict) — human-readable metadata for display
    """
    san_list   = san_list or []
    valid_days = max(1, min(valid_days, 3650))   # cap at 10 years
    key_size   = key_size if key_size in (2048, 4096) else 2048

    # ── 1. Generate RSA private key ───────────────────────────────────────
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )

    # ── 2. Build subject / issuer (same for self-signed) ─────────────────
    name_attrs = [x509.NameAttribute(NameOID.COMMON_NAME, common_name)]
    if org:
        name_attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, org))
    if country:
        name_attrs.append(x509.NameAttribute(NameOID.COUNTRY_NAME, country[:2].upper()))
    if state:
        name_attrs.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state))
    if locality:
        name_attrs.append(x509.NameAttribute(NameOID.LOCALITY_NAME, locality))

    subject = issuer = x509.Name(name_attrs)

    # ── 3. Build SAN extension ────────────────────────────────────────────
    san_entries = []

    # Always add CN as a DNS SAN
    san_entries.append(x509.DNSName(common_name))

    for entry in san_list:
        entry = entry.strip()
        if not entry:
            continue
        try:
            # Try parsing as IP first
            ip = ipaddress.ip_address(entry)
            san_entries.append(x509.IPAddress(ip))
        except ValueError:
            # Treat as DNS name
            san_entries.append(x509.DNSName(entry))

    # ── 4. Build certificate ──────────────────────────────────────────────
    now    = datetime.now(timezone.utc)
    expiry = now + timedelta(days=valid_days)

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(expiry)
        .add_extension(
            x509.SubjectAlternativeName(san_entries),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )

    # ── 5. Serialize to PEM ───────────────────────────────────────────────
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem  = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    logger.info(
        "Generated self-signed cert: cn=%s org=%s days=%d key=%d",
        common_name, org, valid_days, key_size
    )

    return {
        "cert_pem": cert_pem,
        "key_pem":  key_pem,
        "summary": {
            "common_name":   common_name,
            "org":           org or "—",
            "country":       country or "—",
            "valid_from":    now.strftime("%Y-%m-%d"),
            "expiry":        expiry.strftime("%Y-%m-%d"),
            "valid_days":    valid_days,
            "key_size":      key_size,
            "serial":        format(cert.serial_number, "X"),
            "san":           [str(s.value) for s in san_entries],
        },
    }