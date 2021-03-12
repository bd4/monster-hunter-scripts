#!/usr/bin/env python3

import _pathfix

from mhapi.web.wsgi import application

LISTEN_HOST = ""
LISTEN_PORT = 8080

if __name__ == '__main__':
    import sys

    from wsgiref.simple_server import make_server
    httpd = make_server(LISTEN_HOST, LISTEN_PORT, application)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("^C")
