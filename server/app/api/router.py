from fastapi import APIRouter

from app.api import auth, contacts, graph, network, privacy, tags

router = APIRouter(prefix="/v1")

router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(contacts.router, prefix="/me/contacts", tags=["联系人"])
router.include_router(network.router, prefix="/me/network", tags=["网络浏览"])
router.include_router(graph.router, prefix="/me/graph", tags=["关系图"])
router.include_router(privacy.router, prefix="/me", tags=["隐私与账号"])
router.include_router(tags.router, prefix="/tags", tags=["标签"])
