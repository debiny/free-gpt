import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from config import JWT_ALGORITHM, JWT_EXPIRATION_HOURS, JWT_SECRET


def hash_password(plain: str) -> str:
    """Gera um hash PBKDF2-HMAC-SHA256 seguro com salt criptográfico único."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256_200000${salt}${dk.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica se a senha em texto plano confere com o hash fornecido."""
    try:
        parts = hashed.split("$")
        if len(parts) != 3 or parts[0] != "pbkdf2_sha256_200000":
            return False
        salt = parts[1]
        expected_dk_hex = parts[2]
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 200_000)
        return secrets.compare_digest(dk.hex(), expected_dk_hex)
    except Exception:
        return False


def create_token(user_id: str, email: str) -> str:
    """Gera um token JWT com expiração de 7 dias e identificação do usuário."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decodifica e valida a assinatura e expiração de um token JWT."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def token_from_authorization(header: Optional[str]) -> Optional[str]:
    """Extrai a string do token de um cabeçalho Authorization Bearer."""
    if not header:
        return None
    if header.startswith("Bearer "):
        return header[7:].strip()
    return header.strip()
