"""modules/cert_matcher.py — Verify a certificate matches its private key."""
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def check_cert_key_match(cert_file, key_file) -> dict:
    cert_data = cert_file.read()
    key_data  = key_file.read()

    # Load certificate (PEM then DER fallback)
    try:
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    except Exception:
        try:
            cert = x509.load_der_x509_certificate(cert_data, default_backend())
        except Exception as exc:
            return {"error": f"Could not parse certificate: {exc}"}

    # Load private key
    try:
        private_key = serialization.load_pem_private_key(
            key_data, password=None, backend=default_backend()
        )
    except Exception as exc:
        return {"error": f"Could not parse private key: {exc}"}

    # Compare public keys
    fmt = serialization.PublicFormat.SubjectPublicKeyInfo
    enc = serialization.Encoding.PEM

    cert_pub = cert.public_key().public_bytes(encoding=enc, format=fmt)
    key_pub  = private_key.public_key().public_bytes(encoding=enc, format=fmt)

    return {"match": cert_pub == key_pub}
