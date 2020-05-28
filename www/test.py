import orm
# from orm import Model, ModelMetaclass
import asyncio
from models import User, Blog, Comment

loop = asyncio.get_event_loop()
def test():
    yield from orm.creat_pool(loop=loop,user='www-data', password='www-data', db='awesome')

    # u = User(name='Test', email='test@example.com', passwd='1234567890', image='abount:blank',admin=False,id='1')

    # yield from u.save()
    u = yield from User.find('1')
    print('u.name == %s' % u.name)
    yield from u.remove()

loop.run_until_complete(test())