from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import (
    AccountOut,
    DeleteAccountRequest,
    NicknameUpdate,
    PrivacySettingsOut,
    PrivacySettingsUpdate,
)

router = APIRouter()


@router.get("/privacy")
async def get_privacy(user: User = Depends(get_current_user)):
    return {"data": PrivacySettingsOut(
        allow_contacts_visible=user.allow_contacts_visible,
        allow_appear_in_network=user.allow_appear_in_network,
        display_level=user.display_level,
        nickname=user.nickname,
    )}


@router.put("/privacy")
async def update_privacy(body: PrivacySettingsUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.allow_contacts_visible is not None:
        user.allow_contacts_visible = body.allow_contacts_visible
    if body.allow_appear_in_network is not None:
        user.allow_appear_in_network = body.allow_appear_in_network
    if body.display_level is not None:
        if body.display_level not in ("pseudonym_only", "pseudonym_with_group"):
            raise HTTPException(status_code=400, detail="无效的展示级别")
        user.display_level = body.display_level
    await db.commit()
    await db.refresh(user)
    return {"data": PrivacySettingsOut(
        allow_contacts_visible=user.allow_contacts_visible,
        allow_appear_in_network=user.allow_appear_in_network,
        display_level=user.display_level,
        nickname=user.nickname,
    )}


@router.put("/nickname")
async def update_nickname(body: NicknameUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.nickname = body.nickname
    await db.commit()
    return {"data": {"nickname": user.nickname}}


@router.get("/account")
async def get_account(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.auth_method import AuthMethod
    result = await db.execute(select(AuthMethod).where(AuthMethod.user_id == user.id))
    methods = [m.method for m in result.scalars().all()]
    phone_masked = user.phone_hash[:5] + "****" if len(user.phone_hash) > 5 else "****"
    return {"data": {
        "id": str(user.id),
        "phone": phone_masked,
        "auth_methods": methods,
        "created_at": user.created_at.isoformat(),
    }}


@router.post("/export")
async def export_data(user: User = Depends(get_current_user)):
    # Placeholder - will be implemented with OSS in M2
    raise HTTPException(status_code=501, detail="数据导出将在后续版本中开放")


@router.delete("/account")
async def delete_account(body: DeleteAccountRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.confirmation != "DELETE":
        raise HTTPException(status_code=400, detail="请确认删除操作")
    deleted_at = datetime.now(timezone.utc) + timedelta(days=30)
    user.deleted_at = deleted_at
    await db.commit()
    return {"data": {
        "deleted_at": deleted_at.isoformat(),
        "message": "账号已标记删除，30 天内可撤销。到期后数据将彻底清除。",
    }}


@router.post("/account/restore")
async def restore_account(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.deleted_at is None:
        raise HTTPException(status_code=400, detail="账号未被删除")
    user.deleted_at = None
    await db.commit()
    return {"data": {"message": "账号已恢复。"}}
