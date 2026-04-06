import base64
import hashlib
from cryptography.fernet import Fernet

def get_fernet_primary(key_source_str: str) -> Fernet:
    key_source = key_source_str.encode()
    key_hash = hashlib.sha256(key_source).digest()
    fernet_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(fernet_key)

def get_fernet_legacy(key_source_str: str) -> Fernet:
    key = key_source_str
    if len(key) < 32:
        key = key.ljust(32, "0")
    key_bytes = base64.urlsafe_b64encode(key[:32].encode())
    return Fernet(key_bytes)

# Test Key
bridge_key = "W9zP8v2kL5mR3qX7nG4tJ1yH8bF2vS6d"

# 1. Test SHA256 (Primary)
f_primary = get_fernet_primary(bridge_key)
val1 = "Primary Secret"
enc1 = f_primary.encrypt(val1.encode()).decode()

# 2. Test Raw 32 (Legacy)
f_legacy = get_fernet_legacy(bridge_key)
val2 = "Legacy Secret"
enc2 = f_legacy.encrypt(val2.encode()).decode()

# Verification Logic (Simulating the new decrypt_string)
def robust_decrypt(enc_text, key):
    # Try Primary
    try:
        return get_fernet_primary(key).decrypt(enc_text.encode()).decode()
    except:
        # Try Legacy
        try:
            return get_fernet_legacy(key).decrypt(enc_text.encode()).decode()
        except:
            return enc_text

print(f"Decryption Primary: {robust_decrypt(enc1, bridge_key) == val1}")
print(f"Decryption Legacy: {robust_decrypt(enc2, bridge_key) == val2}")
