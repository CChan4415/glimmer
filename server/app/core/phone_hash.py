import hashlib
import hmac

from app.core.config import settings


def hash_phone(phone: str) -> str:
    """HMAC-SHA256 hash of phone number with global salt."""
    return hmac.new(
        settings.phone_hash_salt.encode("utf-8"),
        phone.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
