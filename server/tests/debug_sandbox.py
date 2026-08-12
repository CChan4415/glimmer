import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'
os.environ['APP_ENV'] = 'testing'
import asyncio, json
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.database import Base, get_db
from app.main import app
from app.api import auth as auth_mod

async def main():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    S = async_sessionmaker(engine, expire_on_commit=False)
    async def override_get_db():
        async with S() as s:
            yield s
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        for phone in ['+8613800888001', '+8613800888002', '+8613800888003']:
            await c.post('/v1/auth/send-code', json={'phone': phone})
        codeA = auth_mod._code_store['+8613800888001']['code']
        r = await c.post('/v1/auth/verify', json={'phone': '+8613800888001', 'code': codeA})
        tokenA = r.json()['data']['access_token']
        codeB = auth_mod._code_store['+8613800888002']['code']
        r = await c.post('/v1/auth/verify', json={'phone': '+8613800888002', 'code': codeB})
        tokenB = r.json()['data']['access_token']
        codeC = auth_mod._code_store['+8613800888003']['code']
        r = await c.post('/v1/auth/verify', json={'phone': '+8613800888003', 'code': codeC})
        tokenC = r.json()['data']['access_token']

        await c.post('/v1/me/contacts/batch', headers={'Authorization': f'Bearer {tokenA}'},
                     json={'contacts': [{'name': '张三', 'phone': '+8613800888002', 'group': 'colleague'}]})
        await c.post('/v1/me/contacts/batch', headers={'Authorization': f'Bearer {tokenB}'},
                     json={'contacts': [{'name': '李四', 'phone': '+8613800888003', 'group': 'friend'}]})

        r = await c.get('/v1/me/contacts', headers={'Authorization': f'Bearer {tokenA}'})
        contacts = r.json()['data']
        print('A contacts:', [(x['name'], x['matched_user']) for x in contacts])
        zid = [x for x in contacts if x['name'] == '张三'][0]['id']

        r = await c.get(f'/v1/me/network/second-degree/{zid}', headers={'Authorization': f'Bearer {tokenA}'})
        print('status:', r.status_code)
        print('body:', json.dumps(r.json(), ensure_ascii=False, indent=2))
    await engine.dispose()

asyncio.run(main())
