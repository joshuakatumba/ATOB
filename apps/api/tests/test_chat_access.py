"""FAKE – development only: auth, verification and exhausted quota on chat routes."""
from uuid import UUID, uuid4

import httpx
from civis.quota import mutate
from sqlalchemy import text


async def test_all_chat_routes_require_a_session(chat_clients):
    app, first, _ = chat_clients
    conversation = (await first.post('/v1/conversations', json={'mode': 'research'})).json()['id']
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                base_url='http://localhost:58000') as anonymous:
        for method, path, body in [
            ('GET', '/v1/conversations', None),
            ('POST', '/v1/conversations', {'mode': 'research'}),
            ('GET', '/v1/conversations/' + conversation, None),
            ('PATCH', '/v1/conversations/' + conversation, {'title': 'FAKE'}),
            ('DELETE', '/v1/conversations/' + conversation, None),
            ('POST', '/v1/conversations/' + conversation + '/messages',
             {'content': 'FAKE', 'mode': 'research'}),
            ('POST', '/v1/messages/' + str(uuid4()) + '/feedback', {'rating': 1}),
        ]:
            assert (await anonymous.request(method, path, json=body)).status_code == 401


async def test_exhaustion_creates_no_messages(chat_clients, database):
    _, first, _ = chat_clients
    me = (await first.get('/v1/me')).json()
    await mutate(database, UUID(me['id']), uuid4(), 'spend', 20, 'FAKE exhaustion')
    conversation = (await first.post('/v1/conversations', json={'mode': 'research'})).json()['id']
    path = '/v1/conversations/' + conversation
    response = await first.post(path + '/messages', json={'content': 'FAKE', 'mode': 'research'})
    assert response.status_code == 402
    assert response.json()['error']['code'] == 'quota_exhausted'
    assert (await first.get(path)).json()['messages'] == []


async def test_unverified_session_cannot_stream(chat_clients, database):
    _, first, _ = chat_clients
    me = (await first.get('/v1/me')).json()
    # Use the provider's verification API, never edit its tables or replace its authentication.
    from supertokens_python.recipe.emailverification.asyncio import unverify_email
    from supertokens_python.types import RecipeUserId
    async with database.connect() as connection:
        auth_id = await connection.scalar(text('SELECT auth_user_id FROM users WHERE id=:id'),
                                          {'id': UUID(me['id'])})
    await unverify_email(RecipeUserId(auth_id), me['email'])
    conversation = (await first.post('/v1/conversations', json={'mode': 'research'})).json()['id']
    response = await first.post('/v1/conversations/' + conversation + '/messages',
                                json={'content': 'FAKE', 'mode': 'research'})
    assert response.status_code == 403
    assert response.json()['error']['code'] == 'email_unverified'
    assert (await first.get('/v1/me')).json()['prompts_left'] == 0
