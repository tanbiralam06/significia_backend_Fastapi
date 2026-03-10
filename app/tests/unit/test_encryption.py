import pytest
from app.utils.encryption import encrypt_string, decrypt_string

def test_encryption_decryption():
    test_data = "my-secret-password-123"
    encrypted = encrypt_string(test_data)
    
    assert encrypted != test_data
    assert len(encrypted) > 0
    
    decrypted = decrypt_string(encrypted)
    assert decrypted == test_data

def test_encryption_empty_string():
    assert encrypt_string("") == ""
    assert decrypt_string("") == ""

def test_decryption_failure():
    # Attempting to decrypt corrupted or invalid data should return empty string (as per our implementation)
    assert decrypt_string("invalid-encrypted-data") == ""
