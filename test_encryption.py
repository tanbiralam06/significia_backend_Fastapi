import base64
import hashlib
from cryptography.fernet import Fernet

def get_fernet(key_source_str: str) -> Fernet:
    key_source = key_source_str.encode()
    key_hash = hashlib.sha256(key_source).digest()
    fernet_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(fernet_key)

# Test with the bridge's key
bridge_key = "W9zP8v2kL5mR3qX7nG4tJ1yH8bF2vS6d"
f = get_fernet(bridge_key)

# The encrypted string from the user's screenshot (partial)
# entity_enc = "gAAAAABp0VPn4JIUKQ5HcfssAKPuti2e_0B9aXHqdFFRxsI92Rh4jWkMXXQHukkq2jIF6RXTPH8LS0PyLAKBFJsyZ6Gzxx..."
# I'll just test round-trip
test_val = "Test IA Entity"
enc = f.encrypt(test_val.encode()).decode()
dec = f.decrypt(enc.encode()).decode()

print(f"Decryption success: {dec == test_val}")
print(f"Encrypted starts with: {enc[:10]}")
