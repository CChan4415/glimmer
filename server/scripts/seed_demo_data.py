"""Seed demo data into the real Supabase database.

Creates/uses three users (A/B/C) and a 2-degree chain:
  A knows B, A knows D(unreg); B knows C, B knows E(unreg)

Usage (run on host, connects to Supabase via .env):
    cd server && .venv/bin/python scripts/seed_demo_data.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import engine
from app.core.phone_hash import hash_phone
from app.models.user import User
from app.models.contact import Contact


USERS = {
    "A": {"phone": "+8613800888001", "nickname": "小明"},
    "B": {"phone": "+8613800888002", "nickname": "阿强"},
    "C": {"phone": "+8613800888003", "nickname": "小美"},
}

# Extra unregistered contacts so we also verify unregistered display
EXTRA_A = [{"name": "陈同学", "phone": "+8613800888099", "group": "friend"}]
EXTRA_B = [{"name": "路人甲", "phone": "+8613800888098", "group": "friend"}]


async def create_fresh_user(db, phone, nickname):
    """Create a brand-new user for a fresh phone number.

    Uses entirely new demo numbers (1380088xxxx) not used before, so
    phone_hash stays clean and 2-degree matching works via real phone hashes.
    """
    ph = hash_phone(phone)
    result = await db.execute(select(User).where(User.phone_hash == ph))
    existing = result.scalar_one_or_none()
    if existing is not None:
        print(f"  ⚠️ 冲突：{phone} 已存在用户。换个手机号重试，或手动清理该用户。")
        return existing
    user = User(phone_hash=ph, nickname=nickname)
    db.add(user)
    await db.flush()
    await db.commit()
    print(f"  ✅ 新建用户: {nickname} ({phone})")
    return user


async def ensure_contact(db, owner_id, name, phone, group):
    ph = hash_phone(phone) if phone else None
    existing = None
    if ph:
        result = await db.execute(
            select(Contact).where(Contact.owner_id == owner_id, Contact.phone_hash == ph)
        )
        existing = result.scalar_one_or_none()
    if existing is None:
        contact = Contact(owner_id=owner_id, name=name, phone_hash=ph, group=group)
        db.add(contact)
        await db.flush()
        return contact
    return existing


async def main():
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        print("=" * 50)
        print("播种演示数据到 Supabase")
        print("=" * 50)

        a = await create_fresh_user(db, USERS["A"]["phone"], USERS["A"]["nickname"])
        b = await create_fresh_user(db, USERS["B"]["phone"], USERS["B"]["nickname"])
        c = await create_fresh_user(db, USERS["C"]["phone"], USERS["C"]["nickname"])

        # A knows B (registered), plus an unregistered contact
        print("\n[A 的联系人]")
        await ensure_contact(db, a.id, "张三", USERS["B"]["phone"], "colleague")
        await ensure_contact(db, a.id, "王五", None, "family")
        print("  - 张三 (-> B, 已注册)")
        print("  - 王五 (无手机号, 未注册)")
        for extra in EXTRA_A:
            await ensure_contact(db, a.id, extra["name"], extra["phone"], extra["group"])
            print(f"  - {extra['name']} (未注册)")

        # B knows C (registered), plus an unregistered contact
        print("\n[B 的联系人]")
        await ensure_contact(db, b.id, "李四", USERS["C"]["phone"], "friend")
        print("  - 李四 (-> C, 已注册)")
        for extra in EXTRA_B:
            await ensure_contact(db, b.id, extra["name"], extra["phone"], extra["group"])
            print(f"  - {extra['name']} (未注册)")

        await db.commit()

        print()
        print("=" * 50)
        print("完成！现在 Web 上验证：")
        print("  1. 登录 +8613900138000 (小明)  -> 关系图里张三应显示已注册(绿边)")
        print("  2. 点开张三 -> 查看 TA 的朋友 -> 应看到 李四 (化名: 小美)")
        print("  3. 登录 +8613900138001 (阿强)  -> 也能看到李四(小美)等联系人")
        print("=" * 50)

    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
