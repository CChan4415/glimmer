import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.phone_hash import hash_phone
from app.core.security import create_access_token
from app.models.auth_method import AuthMethod
from app.models.user import User

router = APIRouter()

_code_store: dict = {}

MOCK_SMS = settings.app_env == "development" and not settings.alibaba_access_key_id


def _generate_code() -> str:
    import random
    return f"{random.randint(0, 999999):06d}"


class SendCodeRequest(BaseModel):
    phone: str


class VerifyRequest(BaseModel):
    phone: str
    code: str


class OAuthRequest(BaseModel):
    provider: str
    code: str
    state: str = ""


@router.post("/send-code")
async def send_code(body: SendCodeRequest):
    phone = body.phone.strip()
    if not phone.startswith("+") or len(phone) < 10:
        raise HTTPException(status_code=400, detail="手机号格式无效")

    now = datetime.now(timezone.utc).timestamp()
    last = _code_store.get(phone, {})
    if last and (now - last.get("sent_at", 0)) < 60:
        raise HTTPException(status_code=429, detail="请 60 秒后再试")

    # 单日单号上限 20 条
    day_sent = sum(
        1 for v in _code_store.values()
        if (now - v.get("sent_at", 0)) < 86400 and v.get("phone") == phone
    )
    if day_sent >= 20:
        raise HTTPException(status_code=429, detail="今日发送次数已达上限")

    code = _generate_code()
    _code_store[phone] = {"code": code, "sent_at": now, "attempts": 0}

    if MOCK_SMS:
        print(f"[MOCK SMS] {phone} -> {code}")

    return {"data": {"expires_in": 300, "retry_after": 60}}


@router.post("/verify")
async def verify(body: VerifyRequest, db: AsyncSession = Depends(get_db)):
    phone = body.phone.strip()
    stored = _code_store.get(phone)

    if stored is None:
        raise HTTPException(status_code=400, detail="请先获取验证码")

    now = datetime.now(timezone.utc).timestamp()

    if stored.get("attempts", 0) >= 5 and (now - stored.get("locked_at", 0)) < 600:
        raise HTTPException(status_code=429, detail="验证码错误次数过多，请 10 分钟后再试")

    if stored["code"] != body.code:
        stored["attempts"] = stored.get("attempts", 0) + 1
        if stored["attempts"] >= 5:
            stored["locked_at"] = now
        raise HTTPException(status_code=400, detail="验证码错误")

    if now - stored["sent_at"] > 300:
        raise HTTPException(status_code=400, detail="验证码已过期")

    del _code_store[phone]

    phone_hash = hash_phone(phone)

    result = await db.execute(select(User).where(User.phone_hash == phone_hash))
    user = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        user = User(phone_hash=phone_hash)
        db.add(user)
        await db.flush()

    # Ensure phone auth method exists
    auth_result = await db.execute(
        select(AuthMethod).where(AuthMethod.user_id == user.id, AuthMethod.method == "phone")
    )
    if auth_result.scalar_one_or_none() is None:
        db.add(AuthMethod(user_id=user.id, method="phone", identifier=phone))

    await db.commit()

    token = create_access_token(str(user.id))

    return {
        "data": {
            "access_token": token,
            "refresh_token": token,
            "expires_in": settings.access_token_expire_seconds,
            "user": {"id": str(user.id), "nickname": user.nickname, "is_new": is_new},
        }
    }


@router.post("/oauth")
async def oauth_login(body: OAuthRequest):
    raise HTTPException(status_code=501, detail="第三方登录暂未开放")


@router.post("/refresh")
async def refresh():
    raise HTTPException(status_code=501, detail="暂未开放")


@router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    return None


@router.post("/bind")
async def bind_oauth(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="第三方绑定暂未开放")


@router.delete("/bind/{provider}")
async def unbind(provider: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if provider == "phone":
        raise HTTPException(status_code=400, detail="手机号不可解绑")

    result = await db.execute(
        select(AuthMethod).where(AuthMethod.user_id == user.id, AuthMethod.method == provider)
    )
    method = result.scalar_one_or_none()
    if method is None:
        raise HTTPException(status_code=404, detail="未绑定该方式")

    count_result = await db.execute(select(AuthMethod).where(AuthMethod.user_id == user.id))
    if len(list(count_result.scalars().all())) <= 1:
        raise HTTPException(status_code=400, detail="至少保留一种登录方式")

    await db.delete(method)
    await db.commit()
    return None
