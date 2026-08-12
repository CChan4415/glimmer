from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.contact import Contact
from app.models.user import User


class NetworkRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_registered_first_degree(self, owner_id):
        """Find contacts of owner who have registered accounts (phone_hash matches users)."""
        result = await self.db.execute(
            select(Contact, User)
            .join(User, Contact.phone_hash == User.phone_hash)
            .where(
                Contact.owner_id == owner_id,
                User.deleted_at == None,
                User.allow_appear_in_network == True,
            )
        )
        return list(result.all())

    async def get_second_degree(self, friend_id: str, owner_id: str,
                                friend_allows_contacts: bool,
                                limit: int = 50):
        """Get second-degree contacts for a given 1st-degree friend.

        Privacy checks:
        1. friend's allow_contacts_visible must be True
        2. Me (owner) must have allow_appear_in_network = True
        3. Target users (2nd deg) must have allow_appear_in_network = True (or be unregistered)
        """
        if not friend_allows_contacts:
            return [], 0

        # Find my contacts to compute mutual count
        my_contact_hashes = set()
        my_result = await self.db.execute(
            select(Contact.phone_hash).where(
                Contact.owner_id == owner_id,
                Contact.phone_hash != None,
            )
        )
        for row in my_result.scalars().all():
            if row:
                my_contact_hashes.add(row)

        # Get friend's contacts
        result = await self.db.execute(
            select(Contact)
            .where(Contact.owner_id == friend_id)
            .limit(limit + 1)
        )
        friend_contacts = list(result.scalars().all())
        has_more = len(friend_contacts) > limit
        if has_more:
            friend_contacts = friend_contacts[:limit]

        # Get which of those contacts are registered users
        friend_hashes = [c.phone_hash for c in friend_contacts if c.phone_hash]
        user_lookup = {}
        if friend_hashes:
            u_result = await self.db.execute(
                select(User).where(
                    User.phone_hash.in_(friend_hashes),
                    User.deleted_at == None,
                )
            )
            for u in u_result.scalars().all():
                user_lookup[u.phone_hash] = u

        nodes = []
        for c in friend_contacts:
            matched_user = user_lookup.get(c.phone_hash)
            is_registered = matched_user is not None
            # Privacy: registered users can opt out
            if is_registered and not matched_user.allow_appear_in_network:
                continue
            mutual_count = 1 if c.phone_hash in my_contact_hashes else 0
            display_name = _generate_display(c.name, matched_user)
            group_out = None
            if matched_user and matched_user.display_level == "pseudonym_with_group":
                group_out = c.group
            nodes.append({
                "id": str(c.id),
                "display_name": display_name,
                "group": group_out,
                "mutual_count": mutual_count,
                "is_registered": is_registered,
            })

        return nodes, has_more


def _generate_display(name: str, matched_user: User | None) -> str:
    if matched_user and matched_user.nickname:
        return matched_user.nickname
    if matched_user and matched_user.display_level == "pseudonym_only":
        # Use auto-generated pseudonym
        pass
    # Auto-generate from name
    if not name:
        return "新朋友"
    # Chinese name (2-4 chars): surname + 同学
    if all('一' <= c <= '鿿' for c in name):
        if len(name) <= 1:
            return name + "同学"
        return name[0] + "同学"
    # Non-Chinese: first name
    parts = name.split()
    if len(parts) > 1:
        return parts[0] + " Friend"
    return name[:10] + " Friend" if len(name) > 10 else name + " Friend"
