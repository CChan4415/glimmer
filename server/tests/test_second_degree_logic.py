"""Local unit test for second-degree discovery logic using SQLite.

Tests the core privacy + matching logic without network:
  A(owner) -> B(friend, registered) -> C(2nd degree, registered)
  Also verifies privacy toggles block visibility.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["APP_ENV"] = "testing"

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.phone_hash import hash_phone
from app.models.user import User
from app.models.contact import Contact
from app.repos.network import NetworkRepo, _generate_display


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        # Create users A, B, C
        a = User(phone_hash=hash_phone("+8613900138000"), nickname="A君")
        b = User(phone_hash=hash_phone("+8613900138001"), nickname="B君")
        c = User(phone_hash=hash_phone("+8613900138002"), nickname="C君")
        db.add_all([a, b, c])
        await db.flush()

        # A knows B (registered), and A knows D (unregistered)
        db.add_all([
            Contact(owner_id=a.id, name="张三", phone_hash=b.phone_hash, group="colleague"),
            Contact(owner_id=a.id, name="无名氏", phone_hash=None, group="ungrouped"),
        ])
        # B knows C (registered) and E (unregistered)
        db.add_all([
            Contact(owner_id=b.id, name="王五", phone_hash=c.phone_hash, group="friend"),
            Contact(owner_id=b.id, name="路人甲", phone_hash=None, group="ungrouped"),
        ])
        await db.commit()

        repo = NetworkRepo(db)

        print("=" * 50)
        print("测试 1: A 的已注册 1 度")
        rows = await repo.get_registered_first_degree(a.id)
        assert len(rows) == 1, f"应为 1 个已注册联系人, got {len(rows)}"
        contact_b, user_b = rows[0]
        assert user_b.nickname == "B君"
        print(f"  ✅ A 看到 1 个已注册联系人: {contact_b.name} -> {user_b.nickname}")

        print("=" * 50)
        print("测试 2: A 展开 B 的 2 度")
        nodes, has_more = await repo.get_second_degree(
            friend_id=str(b.id), owner_id=str(a.id),
            friend_allows_contacts=True, limit=50,
        )
        registered = [n for n in nodes if n.is_registered]
        unregistered = [n for n in nodes if not n.is_registered]
        assert len(registered) == 1, f"应有 1 个已注册 2 度 (C), got {len(registered)}"
        assert len(unregistered) == 1, f"应有 1 个未注册 2 度 (路人甲), got {len(unregistered)}"
        c_node = registered[0]
        print(f"  ✅ 看到已注册 2 度: {c_node['display_name']} (化名)")
        print(f"  ✅ 看到未注册 2 度: {unregistered[0]['display_name']} (化名)")
        assert c_node["display_name"] == "C君", "C 应显示昵称"

        print("=" * 50)
        print("测试 3: B 关闭 allow_contacts_visible 后")
        nodes, _ = await repo.get_second_degree(
            friend_id=str(b.id), owner_id=str(a.id),
            friend_allows_contacts=False, limit=50,
        )
        assert len(nodes) == 0, "B 关闭后 A 不应看到任何 2 度"
        print("  ✅ B 关闭后 2 度为空")

        print("=" * 50)
        print("测试 4: C 关闭 allow_appear_in_network 后")
        c.allow_appear_in_network = False
        await db.commit()
        nodes, _ = await repo.get_second_degree(
            friend_id=str(b.id), owner_id=str(a.id),
            friend_allows_contacts=True, limit=50,
        )
        registered = [n for n in nodes if n.is_registered]
        assert len(registered) == 0, "C 关闭后不应出现在 A 的 2 度"
        print("  ✅ C 关闭后从 2 度消失")

        print("=" * 50)
        print("测试 5: 化名生成")
        assert _generate_display("陈小明", None) == "陈同学"
        assert _generate_display("", None) == "新朋友"
        assert _generate_display("John Smith", None) == "John Friend"
        print("  ✅ 中文名 -> 陈同学; 空名 -> 新朋友; 英文名 -> John Friend")

    await engine.dispose()
    print()
    print("🎉 全部 2 度发现逻辑测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
