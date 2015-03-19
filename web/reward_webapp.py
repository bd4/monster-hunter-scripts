#!/usr/bin/env python

import os
import logging

from webob import Request, Response, exc

import mhdb
import mhrewards

# TODO: etag based on db version + manual code version
DB_VERSION = "20150313"
PREFIX = "/mhapi/"

logging.basicConfig(filename="/tmp/reward_webapp.log", level=logging.INFO)

class App(object):
    def __init__(self):
        self.web_path = os.path.dirname(__file__)
        self.project_path = os.path.abspath(os.path.join(self.web_path, ".."))

        db_path = os.path.join(self.project_path, "db", "mh4u.db")
        self.db = mhdb.MHDB(db_path)

        log_path = os.path.join(self.project_path, "web.log")

        self.log = logging.getLogger("reward_webapp")
        self.log.info("app started")

    def __call__(self, environ, start_response):
        req = Request(environ)
        resp = Response()
        resp.charset = "utf8"

        if req.path in ("", "/", "/index.html"):
            resp = self.index(req, resp)
        elif req.path == PREFIX + "rewards":
            resp = self.find_item_rewards(req, resp)
        elif req.path == PREFIX + "item_name_list":
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
        resp.cache_control = "max-age=60"
        resp.etag = DB_VERSION + version

        self.log.info("etag = %s", resp.etag)
        if req.if_match == resp.etag:
            return HTTPNotModified()

        resp.content_type = "text/plan"

        item_name = req.params.get("item_name", "").strip()
        if not item_name:
            resp.body = "Please enter an item name"
        else:
            item_row = mhrewards.find_item(self.db, item_name, resp.body_file)
            if item_row is not None:
                mhrewards.print_quests_and_rewards(self.db, item_row,
                                                   resp.body_file)
        return resp

    def get_all_names(self, req, resp):
        version = "2"
        resp.cache_control = "max-age=60"
        resp.etag = DB_VERSION + version

        self.log.info("get all names etag = %s", resp.etag)
        if req.if_match == resp.etag:
            return HTTPNotModified()

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
    httpd = make_server("localhost", 8080, application)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print "^C"
