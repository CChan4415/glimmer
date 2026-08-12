from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contact import Contact
from app.models.tag import ContactTag


class ContactRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_owner(self, owner_id, group: str | None = None, tag: str | None = None,
                            limit: int = 50, cursor: str | None = None):
        stmt = select(Contact).options(selectinload(Contact.tags)).where(Contact.owner_id == owner_id)
        if group:
            stmt = stmt.where(Contact.group == group)
        if tag:
            stmt = stmt.join(Contact.tags).where(ContactTag.tag == tag).distinct()
        stmt = stmt.order_by(Contact.created_at.desc()).limit(limit + 1)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]
        return rows, has_more

    async def get_by_id(self, contact_id, owner_id=None):
        stmt = select(Contact).where(Contact.id == contact_id)
        if owner_id is not None:
            stmt = stmt.where(Contact.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, owner_id, name, phone_hash=None, group="ungrouped",
                     tags: list[str] | None = None):
        contact = Contact(owner_id=owner_id, name=name, phone_hash=phone_hash, group=group)
        self.db.add(contact)
        await self.db.flush()
        if tags:
            for tag in tags:
                self.db.add(ContactTag(contact_id=contact.id, tag=tag))
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def batch_import(self, owner_id, items: list[dict]):
        imported, skipped = 0, 0
        for item in items:
            if not item.get("name"):
                skipped += 1
                continue
            if item.get("phone_hash"):
                existing = await self.db.execute(
                    select(Contact).where(
                        Contact.owner_id == owner_id,
                        Contact.phone_hash == item["phone_hash"],
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue
            contact = Contact(
                owner_id=owner_id,
                name=item["name"],
                phone_hash=item.get("phone_hash"),
                group=item.get("group", "ungrouped"),
            )
            self.db.add(contact)
            imported += 1
        await self.db.commit()
        return imported, skipped

    async def update(self, contact: Contact, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                setattr(contact, key, value)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def delete(self, contact: Contact):
        await self.db.delete(contact)
        await self.db.commit()

    async def set_tags(self, contact_id, tags: list[str]):
        existing = (await self.db.execute(
            select(ContactTag).where(ContactTag.contact_id == contact_id)
        )).scalars().all()
        for et in existing:
            await self.db.delete(et)
        for tag in tags:
            self.db.add(ContactTag(contact_id=contact_id, tag=tag))
        await self.db.commit()

    async def stats_by_group(self, owner_id) -> dict:
        result = await self.db.execute(
            select(Contact.group, func.count(Contact.id))
            .where(Contact.owner_id == owner_id)
            .group_by(Contact.group)
        )
        rows = result.all()
        stats = {"family": 0, "colleague": 0, "friend": 0, "ungrouped": 0}
        for group_name, count in rows:
            if group_name in stats:
                stats[group_name] = count
        stats["total_contacts"] = sum(stats.values())
        return stats

    async def top_tags(self, owner_id, limit: int = 5) -> dict:
        result = await self.db.execute(
            select(ContactTag.tag, func.count(ContactTag.id))
            .join(Contact, Contact.id == ContactTag.contact_id)
            .where(Contact.owner_id == owner_id)
            .group_by(ContactTag.tag)
            .order_by(func.count(ContactTag.id).desc())
            .limit(limit)
        )
        return dict(result.all())
