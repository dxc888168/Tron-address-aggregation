import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings


def _resolve_master_key() -> bytes:
    settings = get_settings()
    raw = settings.encryption_master_key.strip()

    if not raw:
        raw = settings.jwt_secret

    try:
        decoded = base64.b64decode(raw)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass

    if len(raw) == 64:
        try:
            return bytes.fromhex(raw)
        except ValueError:
            pass

    return hashlib.sha256(raw.encode('utf-8')).digest()


def _fingerprint(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:32]


def encrypt_secret(plaintext: str) -> dict:
    key = _resolve_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    encrypted = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    ciphertext = encrypted[:-16]
    tag = encrypted[-16:]
    return {
        'encrypted_private_key': base64.b64encode(ciphertext).decode('utf-8'),
        'iv': base64.b64encode(nonce).decode('utf-8'),
        'auth_tag': base64.b64encode(tag).decode('utf-8'),
        'checksum_sha256': hashlib.sha256(plaintext.encode('utf-8')).hexdigest(),
        'key_fingerprint': _fingerprint(key),
    }


def decrypt_secret(encrypted_private_key: str, iv: str, auth_tag: str) -> str:
    key = _resolve_master_key()
    aesgcm = AESGCM(key)
    nonce = base64.b64decode(iv)
    ciphertext = base64.b64decode(encrypted_private_key)
    tag = base64.b64decode(auth_tag)
    plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
    return plaintext.decode('utf-8')
