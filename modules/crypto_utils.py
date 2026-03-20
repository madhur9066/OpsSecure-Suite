"""modules/crypto_utils.py — AES (Fernet) encrypt/decrypt and Base64 helpers."""
import base64
import hashlib
from cryptography.fernet import Fernet


def generate_key() -> bytes:
    return Fernet.generate_key()


def aes_encrypt(text: str, key: bytes) -> str:
    return Fernet(key).encrypt(text.encode()).decode()


def aes_decrypt(text: str, key: bytes) -> str:
    return Fernet(key).decrypt(text.encode()).decode()


def generate_hash(text: str, algo: str = "sha256") -> str:
    algos = {
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
        "md5":    hashlib.md5,
    }
    h = algos.get(algo)
    if not h:
        raise ValueError(f"Unsupported algorithm: {algo}")
    return h(text.encode()).hexdigest()


def base64_encode(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def base64_decode(text: str) -> str:
    return base64.b64decode(text.encode()).decode()
