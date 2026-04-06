import base64
import hashlib
import logging
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger("app.encryption")

def _get_fernet_primary() -> Fernet:
    """Primary derivation: SHA256 hashed key (Current Bridge Standard)"""
    key_source = settings.ENCRYPTION_KEY.encode()
    key_hash = hashlib.sha256(key_source).digest()
    fernet_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(fernet_key)

def _get_fernet_legacy() -> Fernet:
    """Legacy derivation: Raw 32-byte key (Original Backend Standard)"""
    key = settings.ENCRYPTION_KEY
    if len(key) < 32:
        key = key.ljust(32, "0")
    key_bytes = base64.urlsafe_b64encode(key[:32].encode())
    return Fernet(key_bytes)

def encrypt_string(data: str) -> str:
    if not data:
        return ""
    # We encrypt using the primary (newest) standard
    f = _get_fernet_primary()
    return f.encrypt(data.encode()).decode()

def decrypt_string(encrypted_data: str) -> str:
    if not encrypted_data:
        return ""
    
    # If it doesn't look like a Fernet token, return as-is
    if not encrypted_data.startswith("gAAAA"):
        return encrypted_data
        
    # Attempt 1: Primary SHA256 derivation
    f_primary = _get_fernet_primary()
    try:
        return f_primary.decrypt(encrypted_data.encode()).decode()
    except Exception:
        # Attempt 2: Legacy raw 32-byte derivation
        f_legacy = _get_fernet_legacy()
        try:
            return f_legacy.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            # Both failed — log warning and return original
            logger.warning(f"Total Decryption Failure — key might be incorrect: {e}")
            return encrypted_data
