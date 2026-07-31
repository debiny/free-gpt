import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt

JWT_SECRET = "change-me-in-production-uses-a-long-random-string"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def hash_password(plain: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 200_000)
    return f"pbkdf2_sha256_200000${salt}${dk.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        parts = hashed.split("$")
        if len(parts) != 3 or parts[0] != "pbkdf2_sha256_200000":
            return False
        _, salt, dk_hex = parts
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 200_000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def token_from_authorization(header: Optional[str]) -> Optional[str]:
    if not header:
        return None
    if header.startswith("Bearer "):
        return header[7:]
    return header
