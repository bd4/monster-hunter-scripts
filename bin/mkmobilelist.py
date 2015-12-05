#!/usr/bin/env python

import sys
import json
import os.path
import types

import _pathfix

from mhapi.db import MHDB
from mhapi.util import get_utf8_writer


def print_header_nav(title, pid):
    print """
  <div data-role="header" data-position="fixed">
    <a href="#page-home" class="ui-btn-left ui-btn ui-btn-inline ui-mini ui-corner-all ui-btn-icon-left ui-icon-home">Home</a>
    <h1>%s</h1>
""".strip() % title

    alt_pid = None
    if pid.endswith("-en"):
        alt_pid = pid.replace("-en", "-jp")
        alt_title = "jp"
    if pid.endswith("-jp"):
        alt_pid = pid.replace("-jp", "-en")
        alt_title = "en"

    if alt_pid is not None:
        print """
    <a href="#%s" class="ui-btn-right ui-btn ui-btn-inline ui-mini">%s</a>
""".strip() % (alt_pid, alt_title)

    print "  </div>"


def mk_html_list(dict_list, keys, sort_keys, divider_fn="auto"):
    if divider_fn == "auto":
        print ('<ul data-role="listview" data-filter="false"'
               ' data-autodividers="true">')
    else:
        print '<ul data-role="listview" data-filter="false">'

    if isinstance(sort_keys, types.FunctionType):
        sort_fn = sort_keys
    else:
        def sort_fn(d):
            return tuple(d[k] for k in sort_keys)
    prev_d = None
    if sort_keys is not None:
        it = sorted(dict_list, key=sort_fn)
    else:
        it = dict_list
    for d in it:
        if divider_fn not in (None, "auto"):
            divider_text = divider_fn(d, prev_d)
            if divider_text is not None:
                print '  <li data-role="list-divider">%s</li>' % divider_text
        print "  <li>"
        for i, k in enumerate(keys):
            value = d[k]
            if k in ("section", "description"):
                if value:
                    print '    <p class="ui-li-desc">%s</p>' % value
                continue
            elif k == "title_jp" and i != 0:
                # NB: for monster by title we want it to be a normal column
                if value:
                    print '    <p class="ui-li-desc">Title: %s</p>' % value
                continue
            if value.endswith(".png"):
                value = ('<img class="icon" src="../img/icons_items/%s" />'
                         % value)
            print '    <span class="%s">%s</span>' % (k, value)
        print "  </li>"
        prev_d = d
    print '</ul>'


def _main():
    db = MHDB()
    #strees = db.get_skill_trees()
    items = db.get_items(item_types=("Tool", "Book", "Consumable", "Ammo"))
    gather_items = db.get_items(item_types=
                ("Bone", "Plant", "Ore", "Fish", "Bug", "Sac/Fluid", "Meat"))

    carve_items = db.get_items(item_types=("Flesh",))


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
      img.icon { width: 20px; height: 20px; }

      .ui-page .ui-content .ui-listview .ui-li-desc {
          white-space : normal;
      }
  </style>

</head>
<body>
<div data-role="page" id="page-home">
  <div data-role="header" data-position="fixed">
    <h1>Home</h1>
  </div>
  <div data-role="main" class="ui-content">
    <ul data-role="listview">
      <li><a href="#page-skilltrees-en">Skill Trees</a></li>
      <li><a href="#page-hunterarts-en">Hunter Arts</a></li>
      <li><a href="#page-monsters-en">Monsters</a></li>
      <li><a href="#page-monsters-title">Monster Titles</a></li>
      <li data-role="list-divider">Items</li>
      <li><a href="#page-item-usable">Usable</a></li>
      <li><a href="#page-item-gather">Gatherable</a></li>
      <li><a href="#page-item-carve">Monster Carves</a></li>
    </ul>
  </div>
</div>
"""
    stree_path = os.path.join(_pathfix.project_path, "db",
                              "mhx_skill_tree_list.json")
    with open(stree_path) as f:
        stree_list = json.load(f)

    print '<div data-role="page" id="page-skilltrees-en">'
    print_header_nav("Skill Trees (en)", "page-skilltrees-en")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(stree_list, ("name", "name_jp"), ("name",))
    print '</div>'
    print '</div>'

    print '<div data-role="page" id="page-skilltrees-jp">'
    print_header_nav("Skill Trees (jp)", "page-skilltrees-jp")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(stree_list, ("name_jp", "name"), jplen_sort_fn,
                              divider_fn=jplen_divider_fn)
    print '</div>'
    print '</div>'

    def item_divider_fn(d, prev_d):
        prefix = _icon_prefix(d)
        prev_prefix = _icon_prefix(prev_d)
        if prefix != prev_prefix:
            return prefix
        return None
    print '<div data-role="page" id="page-item-usable">'
    print_header_nav("Items: Usable", "page-item-usable")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(items, ("icon_name", "name", "name_jp"),
                 ("icon_name", "name"), divider_fn=item_divider_fn)
    print '</div>'
    print '</div>'

    print '<div data-role="page" id="page-item-gather">'
    print_header_nav("Items: Gatherable", "page-item-gather")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(gather_items, ("icon_name", "name", "name_jp"),
                 ("icon_name", "name"), divider_fn=item_divider_fn)
    print '</div>'
    print '</div>'

    print '<div data-role="page" id="page-item-carve">'
    print_header_nav("Items: Carve", "page-item-carve")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(carve_items, ("icon_name", "name", "name_jp"),
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
    print '<div data-role="page" id="page-hunterarts-en">'
    print_header_nav("Hunter Arts (en)", "page-hunterarts-en")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(ha_list, ("name", "name_jp", "description"), None,
                 divider_fn=ha_divider_fn)
    print '</div>'
    print '</div>'

    print '<div data-role="page" id="page-hunterarts-jp">'
    print_header_nav("Hunter Arts (jp)", "page-hunterarts-jp")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(ha_list, ("name_jp", "name", "section", "description"),
                 jplen_sort_fn, divider_fn=jplen_divider_fn)
    print '</div>'
    print '</div>'


    monster_path = os.path.join(_pathfix.project_path, "db",
                                "mhx_monster_list.json")
    with open(monster_path) as f:
        monster_list = json.load(f)

    print '<div data-role="page" id="page-monsters-en">'
    print_header_nav("Monsters (en)", "page-monsters-en")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(monster_list, ("name", "name_jp", "title_jp"), ("name",))
    print '</div>'
    print '</div>'

    print '<div data-role="page" id="page-monsters-jp">'
    print_header_nav("Monsters (jp)", "page-monsters-jp")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(monster_list, ("name_jp", "name", "title_jp"), ("name_jp",))
    print '</div>'
    print '</div>'

    titled_monster_list = [m for m in monster_list if m["title_jp"]]
    print '<div data-role="page" id="page-monsters-title">'
    print_header_nav("Monster Titles", "page-monsters-title")
    print '<div data-role="main" class="ui-content">'
    mk_html_list(titled_monster_list, ("title_jp", "name"), ("title_jp",),
                 divider_fn=None)
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


def jplen_divider_fn(d, prev_d):
    jplen = len(d["name_jp"].strip(" I"))
    if prev_d is None:
        return jplen
    prev_jplen = len(prev_d["name_jp"].strip(" I"))
    if jplen != prev_jplen:
        return jplen
    return None


def jplen_sort_fn(d):
    return (len(d["name_jp"].strip(" I")), d["name_jp"])


if __name__ == '__main__':
    sys.stdout = get_utf8_writer(sys.stdout)
    _main()
