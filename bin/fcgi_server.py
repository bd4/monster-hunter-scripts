#!/usr/bin/env python3

# Set PYTHONPATH in lighttpd or other server config.

from flup.server.fcgi import WSGIServer

from mhapi.web.wsgi import application

if __name__ == '__main__':
    WSGIServer(application).run()
