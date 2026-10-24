"""
AES-256-GCM encryption for sensitive data (CCCD / national ID).
NFR-04: mã hóa CCCD AES-256.
AGENTS.md: Sensitive data (national ID) encrypted at rest; never log PII.
"""
import base64
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings


@lru_cache
def _get_key() -> bytes:
    settings = get_settings()
    key_hex = settings.encryption_key
    return bytes.fromhex(key_hex)


def encrypt(plaintext: str) -> str:
    """Encrypt sensitive string → base64-encoded ciphertext (nonce + tag + ciphertext)."""
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode()


def decrypt(encoded: str) -> str:
    """Decrypt base64-encoded ciphertext → plaintext."""
    key = _get_key()
    aesgcm = AESGCM(key)
    combined = base64.b64decode(encoded)
    nonce = combined[:12]
    ciphertext = combined[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()
