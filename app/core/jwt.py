from datetime import datetime, timedelta, timezone
from app.core.timezone import get_now_ist
from typing import Optional, Dict, Any
from jose import jwt

from app.core.config import settings

def create_access_token(subject: str, tenant_id: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = get_now_ist() + expires_delta
    else:
        expire = get_now_ist() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "tenant_id": str(tenant_id),
        "role": role,
        "type": "access"
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: str, tenant_id: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = get_now_ist() + expires_delta
    else:
        expire = get_now_ist() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "tenant_id": str(tenant_id),
        "type": "refresh"
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.JWTError as e:
        raise ValueError(f"Invalid token: {e}")
