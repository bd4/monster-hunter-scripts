#!/usr/bin/env python

from flup.server.fcgi import WSGIServer

from mhapi.web.wsgi import application

if __name__ == '__main__':
    WSGIServer(application).run()
