"""modules/cert_reader.py — Parse an uploaded PEM/DER certificate file."""
from cryptography import x509
from cryptography.hazmat.backends import default_backend


def parse_certificate(file) -> dict:
    content = file.read()

    try:
        cert = x509.load_pem_x509_certificate(content, default_backend())
    except Exception:
        cert = x509.load_der_x509_certificate(content, default_backend())

    try:
        san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        san = san_ext.value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        san = []

    cn_attrs = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    common_name = cn_attrs[0].value if cn_attrs else "N/A"

    return {
        "common_name":   common_name,
        "issuer":        cert.issuer.rfc4514_string(),
        "valid_from":    cert.not_valid_before,
        "expiry":        cert.not_valid_after,
        "serial_number": str(cert.serial_number),
        "version":       cert.version.name,
        "san":           san,
    }
