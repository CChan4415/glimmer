from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.contact import Contact
from app.models.user import User
from app.repos.contact import ContactRepo
from app.repos.network import _generate_display

router = APIRouter()


@router.get("")
async def get_graph(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ContactRepo(db)
    # Get all 1st degree contacts
    result = await db.execute(
        select(Contact).where(Contact.owner_id == user.id)
    )
    contacts = list(result.scalars().all())

    # Get which of my contacts are registered users
    contact_hashes = [c.phone_hash for c in contacts if c.phone_hash]
    user_lookup = {}
    if contact_hashes:
        u_result = await db.execute(
            select(User).where(User.phone_hash.in_(contact_hashes), User.deleted_at == None)
        )
        for u in u_result.scalars().all():
            user_lookup[u.phone_hash] = u

    # Build nodes (1st degree only, 2nd degree loaded on demand)
    nodes = []
    edges = []

    # Center node (me)
    nodes.append({
        "id": "me",
        "name": user.nickname or "我",
        "group": "center",
        "is_registered": True,
        "is_matched": True,
        "display_name": user.nickname or "我",
        "tags": None,
        "degree": 0,
    })

    for c in contacts:
        matched = user_lookup.get(c.phone_hash)
        node = {
            "id": str(c.id),
            "name": c.name,
            "group": c.group,
            "is_registered": matched is not None,
            "is_matched": False,
            "display_name": _generate_display(c.name, matched),
            "tags": [t.tag for t in c.tags],
            "degree": 1,
        }
        nodes.append(node)
        edges.append({"source": "me", "target": str(c.id)})

    stats_data = await repo.stats_by_group(user.id)
    top_tags = await repo.top_tags(user.id, limit=5)

    return {
        "data": {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_contacts": stats_data["total_contacts"],
                "family": stats_data["family"],
                "colleague": stats_data["colleague"],
                "friend": stats_data["friend"],
                "ungrouped": stats_data["ungrouped"],
                "by_tag": top_tags,
            },
        }
    }
