#!/usr/bin/env python

import os
import logging
import threading

from webob import Request, Response, exc

from mhapi.db import MHDB
from mhapi import rewards

DB_VERSION = "20150313"
PREFIX = "/mhapi/"

# good for testing, use 1 hour = 3600 for deployment
MAX_AGE = "60"

logging.basicConfig(filename="/tmp/reward_webapp.log", level=logging.INFO)


class ThreadLocalDB(threading.local):
    def __init__(self, path):
        threading.local.__init__(self)
        self._db = MHDB(path)

    def __getattr__(self, name):
        return getattr(self._db, name)


class App(object):
    def __init__(self):
        self.web_path = os.path.dirname(__file__)
        self.project_path = os.path.abspath(os.path.join(self.web_path,
                                                         "..", ".."))

        db_path = os.path.join(self.project_path, "db", "mh4u.db")
        self.db = ThreadLocalDB(db_path)

        log_path = os.path.join(self.project_path, "web.log")

        self.log = logging.getLogger("reward_webapp")
        self.log.info("app started")

    def __call__(self, environ, start_response):
        req = Request(environ)
        resp = Response()
        resp.charset = "utf8"

        if req.path_info in ("", "/", "/index.html"):
            resp = self.index(req, resp)
        elif req.path_info == PREFIX + "rewards":
            resp = self.find_item_rewards(req, resp)
        elif req.path_info == PREFIX + "item_name_list":
            resp = self.get_all_names(req, resp)
        else:
            resp = exc.HTTPNotFound()

        return resp(environ, start_response)

    def index(self, req, resp):
        resp.cache_control = "max-age=86400"
        html_path = os.path.join(self.web_path, "index.html")
        resp.content_type = "text/html"
        resp.body = open(html_path, "rb").read()
        return resp

    def find_item_rewards(self, req, resp):
        version = "1"
        etag = DB_VERSION + version
        resp.cache_control = "public, max-age=" + MAX_AGE
        resp.etag = etag

        if etag in req.if_none_match:
            return exc.HTTPNotModified()

        resp.content_type = "text/plain"

        item_name = req.params.get("item_name", "").strip()
        if not item_name:
            resp.body = "Please enter an item name"
        else:
            item_row = rewards.find_item(self.db, item_name, resp.body_file)
            if item_row is not None:
                rewards.print_quests_and_rewards(self.db, item_row,
                                                   resp.body_file)
        return resp

    def get_all_names(self, req, resp):
        version = "2"
        etag = DB_VERSION + version
        resp.cache_control = "public, max-age=" + MAX_AGE
        resp.etag = etag

        if etag in req.if_none_match:
            return exc.HTTPNotModified()

        resp.content_type = "application/json"
        resp.body_file.write("[")
        items = self.db.get_item_names()
        first = True
        for item in items:
            if first:
                first = False
            else:
                resp.body_file.write(", ")
            resp.body_file.write('"')
            resp.body_file.write(item["name"])
            resp.body_file.write('"')
        resp.body_file.write("]")
        return resp


application = App()


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    httpd = make_server("", 8080, application)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print "^C"
