# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    expires_in = settings.jwt_access_token_minutes * 60
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    token = jwt.encode(
        {"sub": subject, "role": role, "exp": expires_at},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in

