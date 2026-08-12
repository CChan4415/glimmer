from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.tag import TagPreset

router = APIRouter()

PRESET_TAGS = [
    ("骑行", "兴趣"), ("摄影", "兴趣"), ("动漫", "兴趣"), ("旅游", "兴趣"),
    ("投资", "兴趣"), ("创业", "兴趣"), ("羽毛球", "兴趣"), ("跑步", "兴趣"),
    ("读书", "兴趣"), ("音乐", "兴趣"), ("美食", "兴趣"), ("游戏", "兴趣"),
    ("AI", "职业"), ("程序员", "职业"), ("设计师", "职业"), ("产品经理", "职业"),
    ("律师", "职业"), ("金融", "职业"), ("医生", "职业"), ("教师", "职业"),
    ("留学生", "生活"), ("数字游民", "生活"), ("宠物", "生活"),
    ("咖啡", "生活"), ("健身", "生活"), ("自驾", "生活"),
]


@router.get("/presets")
async def get_presets(db: AsyncSession = Depends(get_db)):
    # Seed preset tags if table is empty
    result = await db.execute(select(TagPreset))
    existing = result.scalars().all()
    if not existing:
        for i, (tag, category) in enumerate(PRESET_TAGS):
            db.add(TagPreset(tag=tag, category=category, sort_order=i))
        await db.commit()
        result = await db.execute(select(TagPreset).order_by(TagPreset.sort_order))
        existing = result.scalars().all()
    data = [{"tag": t.tag, "category": t.category} for t in existing]
    return {"data": data}
