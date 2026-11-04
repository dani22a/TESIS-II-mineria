from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from .config import settings

ALGO = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_token(user_id: int, sid: str, ttl: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    ttl = ttl if ttl is not None else timedelta(minutes=settings.jwt_ttl_minutes)
    payload = {"sub": str(user_id), "sid": sid, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_token(token: str, verify_exp: bool = True) -> dict:
    return jwt.decode(
        token, settings.jwt_secret, algorithms=[ALGO], options={"verify_exp": verify_exp}
    )
