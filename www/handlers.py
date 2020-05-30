import asyncio, time, re, logging, base64, hashlib, json

import markdown2

from coroweb import get, post

from models import User, Comment, Blog, next_id

from apis import APIValueError, APIResourceNotFoundError, APIError, APIPermissionError, Page

from config import configs

from aiohttp import web

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret
# _COOKIE_KEY = 'Awesome'

# 验证权限
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

# 获取索引
def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as _:
        pass
    if p < 1:
        p = 1
    return p

def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    # build cookie string by: id_expires_sha1
    exprice = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, exprice, _COOKIE_KEY)
    L = [user.id, exprice, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

async def cookie2user(cookie_str):
    '''
    Parse cookie and loda user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

def text2html(text):
    lines = map(lambda s:'<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


# 页面处理-----------------------
# 首页
@get('/')
async def index(*, page='1'):
    # page_inex = get_page_index(page)
    num = await Blog.findNum('count(id)')
    page = Page(num)
    if num == 0:
        blogs = []
    else:
        blogs = await Blog.findAll(order='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'blogs.html',
        'page': page,
        'blogs': blogs
    }

# 注册
@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

# 登录界面
@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

# 管理所有bolg页面
@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }

# 创建blog界面
@get('/manage/blogs/create')
async def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }

# blog详情展示
@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }
#apis--------------------------------

# 登录
@post('/api/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid passwd.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid passwd.')
    # authenticate ok, set cookie:
    r = web.Response()
    cookie = user2cookie(user, 86400)
    logging.info('set_cookie is %s' % cookie)
    r.set_cookie(COOKIE_NAME, cookie, max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    # logging.info('uer ------------ %s' % user)
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

# 登出
@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '_deleted_', max_age=0, httponly=True)
    logging.info('user signed out')
    return r

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+()(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHAL = re.compile(r'^[0-9a-f]{40}$')

#注册用户
@post('/api/users')
async def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHAL.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?',[email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already is use')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

# 创建日志
@post('/api/blogs')
async def api_creat_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name,
    user_image=request.__user__.image,name=name.strip(), summary=summary.strip(),content=content.strip())
    await blog.save()
    return blog

# 获取日志列表
@get('/api/blogs')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNum('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)

#获取日志详情
@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    return blog