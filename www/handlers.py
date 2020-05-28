import asyncio

from coroweb import get, post

from models import User, Comment, Blog, next_id


#首页
@get('/')
async def index(request):
    users = await User.findAll()
    return {
        '__template__' : 'test.html',
        'users': users
    }