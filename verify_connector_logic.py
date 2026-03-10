import sys
import os
import uuid
from typing import Dict, Any

# Mocking settings for the script
class MockSettings:
    ENCRYPTION_KEY = "test-encryption-key-32-byte-long-0"

sys.modules['app.core.config'] = type('config', (), {'settings': MockSettings()})

# Import utilities to test
# We need to add the parent directory to sys.path to find 'app'
sys.path.append(os.getcwd())

try:
    from app.utils.encryption import encrypt_string, decrypt_string
    from app.connectors.database.postgresql import PostgreSQLConnector
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_encryption():
    print("Testing Encryption...")
    original = "secret123"
    encrypted = encrypt_string(original)
    decrypted = decrypt_string(encrypted)
    
    if original == decrypted and original != encrypted:
        print("✅ Encryption/Decryption Success")
    else:
        print(f"❌ Encryption/Decryption Failed: original={original}, decrypted={decrypted}")
        sys.exit(1)

def test_postgresql_logic():
    print("Testing PostgreSQL Connector logic (interface)...")
    config = {
        "host": "localhost",
        "port": 5432,
        "database_name": "test",
        "username": "user",
        "password": "password"
    }
    
    connector = PostgreSQLConnector(config)
    # Testing existence of methods
    if hasattr(connector, 'connect') and hasattr(connector, 'test_connection'):
        print("✅ PostgreSQLConnector Interface Verified")
    else:
        print("❌ PostgreSQLConnector Interface Missing Methods")
        sys.exit(1)

if __name__ == "__main__":
    test_encryption()
    test_postgresql_logic()
    print("\n--- All core logic checks passed! ---")
