import orm
# from orm import Model, ModelMetaclass
import asyncio
from models import User, Blog, Comment

loop = asyncio.get_event_loop()
def test():
    yield from orm.creat_pool(loop=loop,user='www-data', password='www-data', db='awesome')

    # u = User(name='Test', email='test@example.com', passwd='1234567890', image='abount:blank',admin=False,created_at=234141412)

    # yield from u.save()
    u = yield from User.find('001590498103766ea9c323bac034c8289a7b729a7d1cd9b000')
    print('u.name == %s' % u.name)
    yield from u.remove()

loop.run_until_complete(test())