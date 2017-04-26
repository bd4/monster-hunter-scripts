#!/usr/bin/env python

import sys
import json
import os.path
import types
import codecs

from mako.lookup import TemplateLookup
from mako.runtime import Context

import _pathfix

#from mhapi.db import MHDB
from mhapi.util import get_utf8_writer

tlookup = TemplateLookup(directories=["templates/translate"],
                         output_encoding="utf-8",
                         input_encoding="utf-8")
                         #default_filters=["decode.utf8"])
list_template = tlookup.get_template("/list.html")
index_template = tlookup.get_template("/index.html")


def get_auto_divider_fn(field):
    def auto_divider_fn(d, prev_d):
        if prev_d is None:
            prev_first = None
        else:
            prev_first = prev_d[field][:1]
        first = d[field][:1]
        if first != prev_first:
            return first
        return None
    return auto_divider_fn


def mk_html_list(link, title, dict_list, keys, sort_keys, divider_fn="auto"):
    if divider_fn == "auto":
        divider_fn = get_auto_divider_fn(keys[0])
    elif divider_fn is None:
        divider_fn = lambda x, y: None

    alt_link = alt_title = search_link = None
    if link.endswith("-en.html"):
        alt_link = link.replace("-en", "-jp")
        alt_title = "jp"
    elif link.endswith("-jp.html"):
        alt_link = link.replace("-jp", "-en")
        alt_title = "en"
    else:
        search_link = True

    if isinstance(sort_keys, types.FunctionType):
        sort_fn = sort_keys
    else:
        def sort_fn(d):
            return tuple(d[k] for k in sort_keys)

    if sort_keys is not None:
        it = sorted(dict_list, key=sort_fn)
    else:
        it = dict_list

    template_args = dict(
        title=title,
        alt_link=alt_link,
        alt_title=alt_title,
        keys=keys,
        item_list=it,
        divider_fn=divider_fn,
        search_link=search_link
    )

    outpath = os.path.join("web/translate", link)

    with codecs.open(outpath, "w", "utf8") as f:
        ctx = Context(f, **template_args)
        list_template.render_context(ctx)


def _main():
    outpath = "web/translate/index.html"

    with codecs.open(outpath, "w", "utf8") as f:
        ctx = Context(f)
        index_template.render_context(ctx)

    #db = MHDB(game="mhx")
    #strees = db.get_skill_trees()
    #items = db.get_items(item_types=("Tool", "Book", "Consumable", "Ammo"))
    #gather_items = db.get_items(item_types=
    #            ("Bone", "Plant", "Ore", "Fish", "Bug", "Sac/Fluid", "Meat"))

    #carve_items = db.get_items(item_types=("Flesh",))

    stree_path = os.path.join(_pathfix.project_path, "db", "mhxx",
                              "skill_tree_list.json")
    with open(stree_path) as f:
        stree_list = json.load(f)

    mk_html_list("skilltrees-en.html", "Skill Trees (en)",
                 stree_list, ("name", "name_jp"), ("name",))

    mk_html_list("skilltrees-jp.html", "Skill Trees (jp)",
                 stree_list, ("name_jp", "name"), jplen_sort_fn,
                 divider_fn=jplen_divider_fn)

    def item_divider_fn(d, prev_d):
        prefix = _icon_prefix(d)
        prev_prefix = _icon_prefix(prev_d)
        if prefix != prev_prefix:
            return prefix
        return None

    items_path = os.path.join(_pathfix.project_path, "db", "mhx",
                              "items.json")
    with open(items_path) as f:
        items = json.load(f)
    mk_html_list("items-en.html", "Items (en)", items,
                 ("icon_name", "name", "name_jp"), ("icon_name", "name"),
                 divider_fn=item_divider_fn)
    mk_html_list("items-jp.html", "Items (jp)", items,
                 ("icon_name", "name_jp", "name"), ("name_jp",),
                 divider_fn=None)

    carves_path = os.path.join(_pathfix.project_path, "db", "mhx",
                               "monster_carves.json")
    with open(carves_path) as f:
        carves_list = json.load(f)
    mk_html_list("items-carve-en.html", "Items: Carve (en)", carves_list,
                 ("icon_name", "name", "name_jp"), ("icon_name", "name"),
                 divider_fn=item_divider_fn)
    mk_html_list("items-carve-jp.html", "Items: Carve (jp)", carves_list,
                 ("icon_name", "name_jp", "name"), ("name_jp",),
                 divider_fn=None)

    ha_path = os.path.join(_pathfix.project_path,
                           "db", "mhx", "hunter_arts.json")
    with open(ha_path) as f:
        ha_list = json.load(f)

    def ha_divider_fn(d, prev_d):
        if prev_d is None:
            return d["section"]
        elif d["section"] != prev_d["section"]:
            return d["section"]
        return None
    mk_html_list("hunterarts.html", "Hunter Arts", ha_list,
                 ("name", "name_jp", "description"), None,
                 divider_fn=ha_divider_fn)

    #mk_html_list("hunterarts-jp.html", "Hunter Arts (jp)",
    #             ha_list, ("name_jp", "name", "section", "description"),
    #             jplen_sort_fn, divider_fn=jplen_divider_fn)

    monster_path = os.path.join(_pathfix.project_path, "db", "mhxx",
                                "monster_list.json")
    with open(monster_path) as f:
        monster_list = json.load(f)

    mk_html_list("monsters-en.html", "Monsters (en)", monster_list,
                 ("name", "name_jp", "title_jp"), ("name",))

    mk_html_list("monsters-jp.html", "Monsters (jp)", monster_list,
                 ("name_jp", "name", "title_jp"), ("name_jp",))

    titled_monster_list = [m for m in monster_list if m["title_jp"]]
    mk_html_list("monster-titles.html", "Monster Titles", titled_monster_list,
                 ("title_jp", "name"), ("title_jp",), divider_fn=None)


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
