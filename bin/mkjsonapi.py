#!/usr/bin/env python

import os
import json
import sys
import errno
from collections import defaultdict
import urllib

import _pathfix

from mhapi.db import MHDB
from mhapi import model


def mkdirs_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


SAFE_CHARS = " &'+\""


def file_path(path, model_object, use_name=False):
    if use_name and "name" in model_object:
        key = urllib.quote(model_object.name.encode("utf8"), SAFE_CHARS)
    else:
        key = str(model_object.id)
    return os.path.join(path, "%s.json" % key)


def write_list_file(path, model_list):
    list_path = os.path.join(path, "_list.json")
    with open(list_path, "w") as f:
        json.dump([o.as_list_data() for o in model_list], f, indent=2)


def write_index_file(path, indexes):
    index_path = os.path.join(path, "_index.json")
    with open(index_path, "w") as f:
        json.dump(indexes, f, indent=2)


def monster_json(db, path):
    monsters = db.get_monsters()
    mkdirs_p(path)
    write_list_file(path, monsters)

    indexes = {}
    for m in monsters:
        monster_path = file_path(path, m)
        m.update_indexes(indexes)
        data = m.as_data()
        damage = db.get_monster_damage(m.id)
        damage.set_breakable(db.get_monster_breaks(m.id))
        data["damage"] = damage.as_data()
        with open(monster_path, "w") as f:
            json.dump(data, f, cls=model.ModelJSONEncoder, indent=2)

    write_index_file(path, indexes)


def weapon_json(db, path):
    weapons = db.get_weapons()
    mkdirs_p(path)
    write_list_file(path, weapons)

    indexes = {}
    for w in weapons:
        weapon_path = file_path(path, w)
        w.update_indexes(indexes)
        with open(weapon_path, "w") as f:
            w.json_dump(f)

    write_index_file(path, indexes)


def items_json(db, path):
    items = db.get_items()
    mkdirs_p(path)
    write_list_file(path, items)

    indexes = {}
    for item in items:
        item_path = file_path(path, item)
        item.update_indexes(indexes)
        with open(item_path, "w") as f:
            item.json_dump(f)

    write_index_file(path, indexes)


def main():
    db = MHDB(_pathfix.db_path)

    if len(sys.argv) > 1:
        outpath = sys.argv[1]
    else:
        outpath = os.path.join(_pathfix.web_path, "jsonapi")

    items_json(db, os.path.join(outpath, "item"))
    weapon_json(db, os.path.join(outpath, "weapon"))
    monster_json(db, os.path.join(outpath, "monster"))
    #quest_json


if __name__ == '__main__':
    main()
