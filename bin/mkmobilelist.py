#!/usr/bin/env python

import sys
import json
import os.path

import _pathfix

from mhapi.db import MHDB
from mhapi.util import get_utf8_writer


PANEL = """
<div data-role="panel" id="menu" data-display="overlay"
     data-position="fixed">
  <div data-role="navbar">
    <ul>
    <li><a href="#page-skilltrees">Skill Trees</a></li>
    <li><a href="#page-items">Items</a></li>
    </ul>
  </div>
</div>
"""

PANEL2 = """
<div data-role="panel" id="menu" data-display="overlay"
     data-position="fixed">
  <div data-role="controlgroup" data-corners="false">
    <a href="#page-skilltrees">Skill Trees</a>
    <a href="#page-items">Items</a>
  </div>
</div>
"""

def print_header_nav(current_page_id):
    pages = [("page-skilltrees", "Skill Trees"),
             ("page-items", "Items"),
             ("page-hunterarts", "Hunter Arts")]
    print """
<div data-role="header" data-position="fixed">
  <div data-role="navbar">
    <ul>
""".strip("\n")
    for page_id, page_name in pages:
        if current_page_id == page_id:
            print """
      <li><a href="#%s"
             class="ui-btn-active ui-state-persist">%s</a></li>
""".strip("\n") % (page_id, page_name)
        else:
            print """
      <li><a href="#%s">%s</a></li>
""".strip("\n") % (page_id, page_name)
    print """
    </ul>
  </div>
</div>
""".strip("\n")


HEADER_START = """
<div data-role="header" data-position="fixed">
<a href="#menu" data-icon="bars" class="ui-btn-left">Menu</a>
"""


def mk_html_list(dict_list, keys, sort_keys, divider_fn=None):
    if divider_fn is None:
        print ('<ul data-role="listview" data-filter="true"'
               ' data-autodividers="true">')
    else:
        print '<ul data-role="listview" data-filter="true">'

    def sort_fn(d):
        return tuple(d[k] for k in sort_keys)
    prev_d = None
    if sort_keys is not None:
        it = sorted(dict_list, key=sort_fn)
    else:
        it = dict_list
    for d in it:
        if divider_fn is not None:
            divider_text = divider_fn(d, prev_d)
            if divider_text is not None:
                print '  <li data-role="list-divider">%s</li>' % divider_text
        print "  <li>"
        for k in keys:
            value = d[k]
            if k == "description":
                if value:
                    print '    <p class="ui-li-desc">%s</p>' % value
                continue
            if value.endswith(".png"):
                value = ('<img class="icon" src="/img/icons_items/%s" />'
                         % value)
            print '    <span class="%s">%s</span>' % (k, value)
        print "  </li>"
        prev_d = d
    print '</ul>'


def _main():
    db = MHDB()
    strees = db.get_skill_trees()
    items = db.get_items(item_types=("Tool", "Book", "Consumable", "Ammo"))

    print """<!DOCTYPE html>
<html>
<head>
<title>Poogie Translate</title>
<meta charset="utf-8" />

<!-- Include meta tag to ensure proper rendering and touch zooming -->
<meta name="viewport" content="width=device-width, initial-scale=1">

<!-- Include jQuery Mobile stylesheets -->
<link rel="stylesheet" href="http://code.jquery.com/mobile/1.4.5/jquery.mobile-1.4.5.min.css">

<!-- Include the jQuery library -->
<script src="http://code.jquery.com/jquery-1.11.3.min.js"></script>

<!-- Include the jQuery Mobile library -->
<script src="http://code.jquery.com/mobile/1.4.5/jquery.mobile-1.4.5.min.js"></script>

  <style>
      span.name { display: inline-block; min-width: 50%; }
      span.name_jp { display: inline-block; min-width: 50%; }
      img.icon { width: 20px; height: 20px; }

      .ui-page .ui-content .ui-listview .ui-li-desc {
          white-space : normal;
      }
  </style>

</head>
<body>
"""

    print '<div data-role="page" id="page-skilltrees">'
    #print PANEL
    #print HEADER_START
    #print '<h2>Skill Trees</h2>'
    #print '</div>'
    #print HEADER_NAV
    print_header_nav("page-skilltrees")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(strees, ("name", "name_jp"), ("name",))
    print '</div>'
    print '</div>'

    def item_divider_fn(d, prev_d):
        prefix = _icon_prefix(d)
        prev_prefix = _icon_prefix(prev_d)
        if prefix != prev_prefix:
            return prefix
        return None
    print '<div data-role="page" id="page-items">'
    #print PANEL
    #print HEADER_START
    #print '<h2>Items</h2>'
    #print '</div>'
    #print HEADER_NAV
    print_header_nav("page-items")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(items, ("icon_name", "name", "name_jp"),
                 ("icon_name", "name"), divider_fn=item_divider_fn)
    print '</div>'
    print '</div>'

    ha_path = os.path.join(_pathfix.project_path, "db", "hunter_arts.json")
    with open(ha_path) as f:
        ha_list = json.load(f)

    def ha_divider_fn(d, prev_d):
        if prev_d is None:
            return d["section"]
        elif d["section"] != prev_d["section"]:
            return d["section"]
        return None
    print '<div data-role="page" id="page-hunterarts">'
    print_header_nav("page-hunterarts")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(ha_list, ("name", "name_jp", "description"), None,
                 divider_fn=ha_divider_fn)
    print '</div>'
    print '</div>'

    print """
</body>
"""

def _icon_prefix(d):
    if d is None:
        return ""
    parts = d["icon_name"].split("-", 1)
    return parts[0].replace(".png", "")


if __name__ == '__main__':
    sys.stdout = get_utf8_writer(sys.stdout)
    _main()
