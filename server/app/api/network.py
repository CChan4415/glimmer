import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repos.network import NetworkRepo

router = APIRouter()


@router.get("/first-degree")
async def list_first_degree(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = NetworkRepo(db)
    rows = await repo.get_registered_first_degree(user.id)
    data = []
    for contact, matched_user in rows:
        data.append({
            "contact_id": str(contact.id),
            "name": contact.name,
            "group": contact.group,
            "matched_user": {
                "id": str(matched_user.id),
                "nickname": matched_user.nickname,
                "display_level": matched_user.display_level,
            },
        })
    return {"data": data}


@router.get("/second-degree/{contact_id}")
async def list_second_degree(
    contact_id: uuid.UUID,
    limit: int = Query(50, le=200),
    cursor: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.contact import Contact
    from sqlalchemy import select

    # Verify contact belongs to me
    c_result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.owner_id == user.id)
    )
    my_contact = c_result.scalar_one_or_none()
    if my_contact is None:
        raise HTTPException(status_code=404, detail="联系人不存在")

    # Check if this contact is a registered user
    if my_contact.phone_hash is None:
        raise HTTPException(status_code=403, detail="该联系人未注册")

    u_result = await db.execute(
        select(User).where(User.phone_hash == my_contact.phone_hash, User.deleted_at == None)
    )
    friend = u_result.scalar_one_or_none()
    if friend is None:
        raise HTTPException(status_code=403, detail="该联系人未注册")

    if not friend.allow_contacts_visible:
        return {"data": [], "meta": {"source_contact": {"id": str(my_contact.id), "display_name": friend.nickname or "用户"}, "total": 0}, "pagination": {"next_cursor": None, "has_more": False}}

    repo = NetworkRepo(db)
    nodes, has_more = await repo.get_second_degree(
        friend_id=str(friend.id),
        owner_id=str(user.id),
        friend_allows_contacts=friend.allow_contacts_visible,
        limit=limit,
    )

    return {
        "data": nodes,
        "meta": {
            "source_contact": {
                "id": str(my_contact.id),
                "display_name": (friend.nickname or "用户"),
            },
            "total": len(nodes),
        },
        "pagination": {"next_cursor": None, "has_more": has_more},
    }
