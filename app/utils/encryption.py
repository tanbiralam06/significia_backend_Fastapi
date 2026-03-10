import base64
from cryptography.fernet import Fernet
from app.core.config import settings

def _get_fernet() -> Fernet:
    # Ensure the key is valid Fernet (32-byte base64 encoded)
    # For dev, we might need to pad/truncate if not exact 32 bytes
    key = settings.ENCRYPTION_KEY
    if len(key) < 32:
        key = key.ljust(32, "0")
    key_bytes = base64.urlsafe_b64encode(key[:32].encode())
    return Fernet(key_bytes)

def encrypt_string(data: str) -> str:
    if not data:
        return ""
    f = _get_fernet()
    return f.encrypt(data.encode()).decode()

def decrypt_string(encrypted_data: str) -> str:
    if not encrypted_data:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception:
        # If decryption fails (e.g. wrong key or corrupted data)
        return ""
