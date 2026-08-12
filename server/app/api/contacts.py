import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.phone_hash import hash_phone
from app.repos.contact import ContactRepo
from app.schemas.common import (
    ContactBatchImport,
    ContactCreate,
    ContactOut,
    ContactUpdate,
    MatchedUserOut,
)
from app.models.user import User

router = APIRouter()


def _to_contact_out(contact, user_lookup: dict) -> ContactOut:
    """Convert a Contact ORM object to ContactOut, adding matched_user info."""
    matched = None
    if contact.phone_hash and contact.phone_hash in user_lookup:
        u = user_lookup[contact.phone_hash]
        matched = MatchedUserOut(id=str(u.id), nickname=u.nickname)
    return ContactOut(
        id=str(contact.id),
        name=contact.name,
        phone_hash=contact.phone_hash,
        group=contact.group,
        is_manual=contact.is_manual,
        tags=[t.tag for t in contact.tags],
        last_contacted_at=contact.last_contacted_at,
        matched_user=matched,
        created_at=contact.created_at,
    )


@router.get("")
async def list_contacts(
    group: str | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(50, le=200),
    cursor: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ContactRepo(db)
    rows, has_more = await repo.list_by_owner(user.id, group=group, tag=tag, limit=limit)
    # Build user lookup for matched contacts
    hashes = [r.phone_hash for r in rows if r.phone_hash]
    from sqlalchemy import select
    if hashes:
        u_result = await db.execute(select(User).where(User.phone_hash.in_(hashes)))
        user_lookup = {u.phone_hash: u for u in u_result.scalars().all()}
    else:
        user_lookup = {}
    data = [_to_contact_out(r, user_lookup) for r in rows]
    return {"data": data, "pagination": {"next_cursor": str(rows[-1].id) if has_more else None, "has_more": has_more}}


@router.get("/{contact_id}")
async def get_contact(contact_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = ContactRepo(db)
    contact = await repo.get_by_id(contact_id, owner_id=user.id)
    if contact is None:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return _to_contact_out(contact, {})


@router.post("", status_code=201)
async def create_contact(body: ContactCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = ContactRepo(db)
    phone_hash_val = hash_phone(body.phone) if body.phone else None
    contact = await repo.create(
        owner_id=user.id,
        name=body.name,
        phone_hash=phone_hash_val,
        group=body.group,
        tags=body.tags,
    )
    return _to_contact_out(contact, {})


@router.post("/batch")
async def batch_import(body: ContactBatchImport, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if len(body.contacts) > 500:
        raise HTTPException(status_code=413, detail="单次最多导入 500 人")
    items = []
    for c in body.contacts:
        if not c.name:
            continue
        items.append({
            "name": c.name,
            "phone_hash": hash_phone(c.phone) if c.phone else None,
            "group": c.group,
        })
    repo = ContactRepo(db)
    imported, skipped = await repo.batch_import(user.id, items)
    stats = await repo.stats_by_group(user.id)
    return {"data": {"imported": imported, "skipped": skipped, "skipped_reason": "duplicate_or_no_name", "summary": stats}}


@router.put("/{contact_id}")
async def update_contact(contact_id: uuid.UUID, body: ContactUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = ContactRepo(db)
    contact = await repo.get_by_id(contact_id, owner_id=user.id)
    if contact is None:
        raise HTTPException(status_code=404, detail="联系人不存在")
    kwargs = body.model_dump(exclude_unset=True)
    tags = kwargs.pop("tags", None)
    if kwargs:
        await repo.update(contact, **kwargs)
    if tags is not None:
        await repo.set_tags(contact.id, tags)
    await db.refresh(contact)
    return _to_contact_out(contact, {})


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = ContactRepo(db)
    contact = await repo.get_by_id(contact_id, owner_id=user.id)
    if contact is None:
        raise HTTPException(status_code=404, detail="联系人不存在")
    await repo.delete(contact)
    return None
