import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web,web_runner

routes = web.RouteTableDef()

@routes.get('/')
def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')


def init():
    app = web.Application()
    app.add_routes([web.get('/', index)])
    logging.info('server started at http://127.0.0.1:9257...')
    web.run_app(app, host='127.0.0.1', port=9527)

init()
